from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd

from app.engines.risk.instruments import InstrumentRegistry, InstrumentSpec, AssetClass
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest, PreFlightTradeResponse


@dataclass
class BacktestTrade:
    entry_bar: int
    exit_bar: int
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    r_multiple: float
    exit_reason: str
    position_size_lots: float = 0.1
    decision_id: Optional[str] = None
    spread_paid_pips: float = 0.0
    was_news_trade: bool = False


@dataclass
class BacktestResult:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    expectancy_usd: float
    max_drawdown: float
    max_drawdown_pct: float
    net_profit: float
    net_profit_pct: float
    sharpe_ratio: float
    avg_rr: float
    consecutive_losses: int
    total_bars: int
    trades: List[BacktestTrade]
    equity_curve: List[float]
    drawdown_curve: List[float]
    initial_capital: float = 10000.0
    vetoed_signals_count: int = 0
    veto_reasons_summary: Dict[str, int] = field(default_factory=dict)
    total_slippage_pips_incurred: float = 0.0

    def __contains__(self, key: str) -> bool:
        return key in ("metrics", "equity_curve", "trades", "drawdown_curve")

    def __getitem__(self, item: str) -> Any:
        if item == "metrics":
            return {
                "initial_balance": self.initial_capital,
                "total_trades": self.total_trades,
                "win_rate": self.win_rate,
                "max_drawdown_pct": self.max_drawdown_pct,
            }
        elif item == "equity_curve":
            return self.equity_curve
        elif item == "trades":
            return self.trades
        elif item == "drawdown_curve":
            return self.drawdown_curve
        raise KeyError(item)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default


def generate_synthetic_ohlcv(
    n_bars: int = 500,
    base_price: float = 1.1000,
    volatility: float = 0.002,
    seed: Optional[int] = None,
) -> pd.DataFrame:
    if seed is not None:
        np.random.seed(seed)
    else:
        np.random.seed(42)

    returns = np.random.normal(0, volatility, n_bars)
    close_prices = base_price * np.exp(np.cumsum(returns))

    high_prices = close_prices * (1 + np.abs(np.random.normal(0, volatility * 0.5, n_bars)))
    low_prices = close_prices * (1 - np.abs(np.random.normal(0, volatility * 0.5, n_bars)))
    open_prices = close_prices * (1 + np.random.normal(0, volatility * 0.3, n_bars))

    high_prices = np.maximum(high_prices, np.maximum(open_prices, close_prices))
    low_prices = np.minimum(low_prices, np.minimum(open_prices, close_prices))

    volume = np.random.randint(100, 10000, n_bars).astype(float)

    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n_bars, freq="h"),
        "open": open_prices,
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
        "volume": volume,
    })


class DeterministicBacktestEngine:
    def __init__(
        self,
        initial_capital: float = 10000.0,
        risk_per_trade: float = 1.0,
        slippage_pips: float = 0.5,
        commission_per_lot: float = 7.0,
        symbol: str = "EURUSD",
        initial_balance: Optional[float] = None,
        risk_percent: Optional[float] = None,
        gatekeeper: Optional[PreFlightGatekeeper] = None,
        registry: Optional[InstrumentRegistry] = None,
        **kwargs,
    ):
        self.initial_capital = float(initial_balance if initial_balance is not None else initial_capital)
        current_risk = risk_percent if risk_percent is not None else risk_per_trade
        self.risk_pct = float(current_risk)
        self.risk_per_trade = self.risk_pct / 100.0
        self.slippage_pips = float(slippage_pips)
        self.commission_per_lot = float(commission_per_lot)
        
        self.registry = registry or InstrumentRegistry()
        raw_sym = symbol or "EURUSD"
        try:
            self.canonical_symbol = self.registry.normalize_symbol(raw_sym)
            self.spec = self.registry.get_spec(self.canonical_symbol)
        except Exception:
            self.canonical_symbol = "EURUSD"
            self.spec = self.registry.get_spec("EURUSD")

        self.gatekeeper = gatekeeper or PreFlightGatekeeper(instrument_registry=self.registry)

    def _calculate_variable_spread(self, base_spread: float, volume: float, max_volume: float) -> float:
        if max_volume <= 0:
            return base_spread
        volume_ratio = volume / max_volume
        if volume_ratio < 0.15:
            return base_spread * 3.5
        elif volume_ratio > 0.85:
            return base_spread * 2.0
        return base_spread

    def _apply_slippage(self, price: float, direction: str, is_entry: bool, multiplier: float = 1.0) -> float:
        pip = self.spec.pip_unit
        slip = self.slippage_pips * pip * multiplier
        if direction in ("LONG", "BUY"):
            return price + slip if is_entry else price - slip
        else:
            return price - slip if is_entry else price + slip

    def _apply_commission(self, position_size_lots: float) -> float:
        return self.commission_per_lot * position_size_lots

    def run_simulation(
        self,
        df: pd.DataFrame,
        strategy_id: str = "trend_continuation",
        allow_news_trading: bool = False,
    ) -> BacktestResult:
        if len(df) < 20:
            raise ValueError(f"Minimum 20 bars required, got {len(df)}")

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values if "volume" in df.columns else np.ones(len(closes)) * 1000.0
        max_vol = float(np.max(volumes)) if len(volumes) > 0 else 1000.0
        n = len(closes)

        equity = float(self.initial_capital)
        equity_curve = [equity]
        drawdown_curve = [0.0]
        peak_equity = equity

        trades: List[BacktestTrade] = []
        in_position = False
        direction = ""
        entry_price = 0.0
        entry_bar = 0
        stop_loss = 0.0
        take_profit = 0.0
        position_size_lots = 0.0
        active_decision_id: Optional[str] = None
        was_news_trade = False

        vetoed_signals_count = 0
        veto_reasons_summary: Dict[str, int] = {}
        consecutive_losses = 0
        total_slippage_incurred = 0.0

        atr_period = min(14, max(2, n // 3))
        atr_values = np.zeros(n)
        for i in range(atr_period, n):
            tr_sum = 0.0
            for j in range(i - atr_period + 1, i + 1):
                tr = max(
                    highs[j] - lows[j],
                    abs(highs[j] - closes[j - 1]),
                    abs(lows[j] - closes[j - 1]),
                )
                tr_sum += tr
            atr_values[i] = tr_sum / atr_period

        start_bar = min(atr_period + 1, n - 1)
        for i in range(start_bar, n):
            atr = atr_values[i] if atr_values[i] > 0 else (closes[i] * 0.001)

            is_news_hour = False
            if "timestamp" in df.columns:
                try:
                    hour = pd.to_datetime(df["timestamp"].values[i]).hour
                    is_news_hour = hour in (13, 14, 15)
                except Exception:
                    is_news_hour = False

            base_spec_spread = self.spec.max_allowed_spread_pips * 0.4
            current_spread = self._calculate_variable_spread(base_spec_spread, volumes[i], max_vol)
            
            slip_multiplier = 1.0
            if is_news_hour:
                current_spread *= 4.0
                slip_multiplier = 3.0

            if not in_position:
                signal = self._generate_signal(closes, highs, lows, i, atr, strategy_id)
                if signal != "NONE":
                    direction = "BUY" if signal == "LONG" else "SELL"
                    raw_entry = closes[i]
                    proposed_entry = self._apply_slippage(raw_entry, direction, is_entry=True, multiplier=slip_multiplier)

                    sl_distance = atr * 1.5
                    tp_distance = atr * 2.5

                    if direction == "BUY":
                        stop_loss = proposed_entry - sl_distance
                        take_profit = proposed_entry + tp_distance
                    else:
                        stop_loss = proposed_entry + sl_distance
                        take_profit = proposed_entry - tp_distance

                    current_dd_pct = max(0.0, (peak_equity - equity) / peak_equity * 100) if peak_equity > 0 else 0.0
                    gate_req = PreFlightTradeRequest(
                        symbol=self.canonical_symbol,
                        direction=direction,
                        entry_price=proposed_entry,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        account_balance=equity,
                        risk_per_trade_pct=self.risk_pct,
                        consecutive_losses=consecutive_losses,
                        current_total_drawdown_pct=current_dd_pct,
                        current_spread_pips=current_spread,
                        is_news_blackout=is_news_hour,
                        allow_news_trading=allow_news_trading,
                    )

                    gate_res: PreFlightTradeResponse = self.gatekeeper.evaluate(gate_req)

                    if not gate_res.allowed:
                        vetoed_signals_count += 1
                        for r in gate_res.rejection_reasons:
                            veto_reasons_summary[r] = veto_reasons_summary.get(r, 0) + 1
                    else:
                        entry_price = proposed_entry
                        position_size_lots = gate_res.approved_lot_size
                        active_decision_id = gate_res.decision_id
                        was_news_trade = is_news_hour
                        total_slippage_incurred += self.slippage_pips * slip_multiplier
                        entry_bar = i
                        in_position = True

            else:
                exit_price = 0.0
                exit_reason = ""

                if direction == "BUY":
                    if lows[i] <= stop_loss:
                        exit_price = self._apply_slippage(stop_loss, direction, is_entry=False, multiplier=slip_multiplier)
                        exit_reason = "STOP_LOSS"
                    elif highs[i] >= take_profit:
                        exit_price = self._apply_slippage(take_profit, direction, is_entry=False, multiplier=slip_multiplier)
                        exit_reason = "TAKE_PROFIT"
                else:
                    if highs[i] >= stop_loss:
                        exit_price = self._apply_slippage(stop_loss, direction, is_entry=False, multiplier=slip_multiplier)
                        exit_reason = "STOP_LOSS"
                    elif lows[i] <= take_profit:
                        exit_price = self._apply_slippage(take_profit, direction, is_entry=False, multiplier=slip_multiplier)
                        exit_reason = "TAKE_PROFIT"

                if exit_price > 0:
                    pip_unit = self.spec.pip_unit

                    if direction == "BUY":
                        price_diff = exit_price - entry_price
                    else:
                        price_diff = entry_price - exit_price

                    pip_gain = price_diff / pip_unit
                    pip_val_usd = self.gatekeeper._calculate_pip_value(self.spec, entry_price, {})
                    raw_pnl = pip_gain * pip_val_usd * position_size_lots

                    commission = self._apply_commission(position_size_lots)
                    pnl = raw_pnl - commission
                    pnl_pct = (pnl / equity) * 100 if equity > 0 else 0

                    sl_distance = abs(entry_price - stop_loss)
                    r_multiple = (price_diff / sl_distance) if sl_distance > 0 else 0.0

                    if pnl <= 0:
                        consecutive_losses += 1
                    else:
                        consecutive_losses = 0

                    trades.append(BacktestTrade(
                        entry_bar=entry_bar,
                        exit_bar=i,
                        direction=direction,
                        entry_price=round(float(entry_price), 6),
                        exit_price=round(float(exit_price), 6),
                        pnl=round(float(pnl), 2),
                        pnl_pct=round(float(pnl_pct), 2),
                        r_multiple=round(float(r_multiple), 2),
                        exit_reason=exit_reason,
                        position_size_lots=position_size_lots,
                        decision_id=active_decision_id,
                        spread_paid_pips=round(float(current_spread), 2),
                        was_news_trade=was_news_trade,
                    ))

                    total_slippage_incurred += self.slippage_pips * slip_multiplier
                    equity += pnl
                    in_position = False

            equity_curve.append(round(float(equity), 2))
            if equity > peak_equity:
                peak_equity = equity
            dd = (peak_equity - equity) / peak_equity * 100 if peak_equity > 0 else 0
            drawdown_curve.append(round(float(dd), 2))

        metrics = self._compute_metrics(trades, equity, n)

        return BacktestResult(
            **metrics,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_curve=drawdown_curve,
            initial_capital=self.initial_capital,
            vetoed_signals_count=vetoed_signals_count,
            veto_reasons_summary=veto_reasons_summary,
            total_slippage_pips_incurred=round(float(total_slippage_incurred), 1),
        )

    def _generate_signal(
        self,
        closes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        i: int,
        atr: float,
        strategy_id: str,
    ) -> str:
        if i < 10:
            return "NONE"

        lookback_fast = min(9, i)
        lookback_slow = min(20, i)
        sma_fast = np.mean(closes[i - lookback_fast:i + 1])
        sma_slow = np.mean(closes[i - lookback_slow:i + 1])

        if strategy_id == "mean_reversion":
            gains = 0.0
            losses = 0.0
            rsi_lookback = min(14, i)
            for j in range(i - rsi_lookback + 1, i + 1):
                diff = closes[j] - closes[j - 1]
                if diff > 0:
                    gains += diff
                else:
                    losses += abs(diff)
            rs = gains / losses if losses > 0 else 100
            rsi = 100 - (100 / (1 + rs))

            if rsi < 30 and closes[i] > closes[i - 1]:
                return "LONG"
            elif rsi > 70 and closes[i] < closes[i - 1]:
                return "SHORT"
        else:
            if sma_fast > sma_slow and closes[i] > sma_fast and closes[i] > closes[i - 1]:
                return "LONG"
            elif sma_fast < sma_slow and closes[i] < sma_fast and closes[i] < closes[i - 1]:
                return "SHORT"

        return "NONE"

    def _compute_metrics(
        self, trades: List[BacktestTrade], final_equity: float, total_bars: int
    ) -> Dict[str, Any]:
        if not trades:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate": 0.0, "profit_factor": 0.0, "expectancy_r": 0.0,
                "expectancy_usd": 0.0, "max_drawdown": 0.0, "max_drawdown_pct": 0.0,
                "net_profit": 0.0, "net_profit_pct": 0.0, "sharpe_ratio": 0.0,
                "avg_rr": 0.0, "consecutive_losses": 0, "total_bars": total_bars,
            }

        pnls = [t.pnl for t in trades]
        r_multiples = [t.r_multiple for t in trades]
        winners = [p for p in pnls if p > 0]
        losers = [p for p in pnls if p <= 0]

        total_trades = len(trades)
        winning_trades = len(winners)
        losing_trades = len(losers)
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0

        gross_profit = sum(winners) if winners else 0
        gross_loss = abs(sum(losers)) if losers else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 999.99

        expectancy_r = sum(r_multiples) / total_trades if total_trades > 0 else 0
        expectancy_usd = sum(pnls) / total_trades if total_trades > 0 else 0

        net_profit = final_equity - self.initial_capital
        net_profit_pct = (net_profit / self.initial_capital) * 100

        peak = self.initial_capital
        max_dd = 0.0
        max_dd_pct = 0.0
        running_equity = self.initial_capital
        for p in pnls:
            running_equity += p
            if running_equity > peak:
                peak = running_equity
            dd = peak - running_equity
            dd_pct = (dd / peak) * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        if len(pnls) > 1:
            returns = np.array(pnls) / self.initial_capital
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252 * 24) if np.std(returns) > 0 else 0
        else:
            sharpe = 0.0

        tp_trades = [t for t in trades if t.exit_reason == "TAKE_PROFIT"]
        sl_trades = [t for t in trades if t.exit_reason == "STOP_LOSS"]
        avg_rr = (len(tp_trades) / len(sl_trades)) if sl_trades else 999.99

        max_consec = 0
        current_consec = 0
        for p in pnls:
            if p <= 0:
                current_consec += 1
                max_consec = max(max_consec, current_consec)
            else:
                current_consec = 0

        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(float(win_rate), 2),
            "profit_factor": round(float(profit_factor), 2),
            "expectancy_r": round(float(expectancy_r), 3),
            "expectancy_usd": round(float(expectancy_usd), 2),
            "max_drawdown": round(float(max_dd), 2),
            "max_drawdown_pct": round(float(max_dd_pct), 2),
            "net_profit": round(float(net_profit), 2),
            "net_profit_pct": round(float(net_profit_pct), 2),
            "sharpe_ratio": round(float(sharpe), 3),
            "avg_rr": round(float(avg_rr), 2),
            "consecutive_losses": max_consec,
            "total_bars": total_bars,
        }
