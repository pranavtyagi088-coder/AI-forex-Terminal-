from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional
from app.models.instrument import Instrument
from app.engines.risk.calculator import calculate_position_size, RiskRequest


@dataclass
class TradeCalculationResult:
    direction: str
    entry_price: float
    stop_loss: float
    take_profit: float
    stop_loss_pips: float
    take_profit_pips: float
    risk_reward_ratio: float
    position_size_lots: float
    risk_amount_usd: float
    is_valid_rr: bool
    rejection_reason: Optional[str] = None


class DeterministicTradeCalculator:
    """
    Computes exact entry, SL, TP, RR, and Position Size
    strictly from deterministic math and canonical risk engine.
    """

    @staticmethod
    def calculate_trade(
        strategy_rules: Optional[Dict[str, Any]],
        market_state: Dict[str, Any],
        instrument: Instrument,
        account_balance: float,
        risk_percent: float,
        direction: str,
        exchange_rate: float = 1.0,
        live_rates: Optional[Dict[str, float]] = None
    ) -> TradeCalculationResult:
        rules = strategy_rules or {}
        if live_rates is None:
            live_rates = {}

        pip_size = float(instrument.pip_size)
        contract_size = float(instrument.contract_size)
        quote_cur = getattr(instrument, "quote_currency", "USD") or "USD"

        if exchange_rate and exchange_rate != 1.0 and f"USD{quote_cur}" not in live_rates:
            live_rates[f"USD{quote_cur}"] = exchange_rate

        current_price = float(market_state.get("current_price", 0.0))
        atr = float(market_state.get("atr", pip_size * 20.0))
        swing_high = float(market_state.get("swing_high", current_price + (atr * 2)))
        swing_low = float(market_state.get("swing_low", current_price - (atr * 2)))

        stop_rules = rules.get("stop_conditions", {})
        tp_rules = rules.get("take_profit_conditions", {})
        min_rr = float(rules.get("min_acceptable_rr", 1.5))

        atr_multiplier = float(stop_rules.get("atr_multiplier", 1.5))
        tp_atr_multiplier = float(tp_rules.get("atr_multiplier", 3.0))
        tp_fixed_rr = tp_rules.get("target_rr", None)

        entry_price = round(current_price, 5)

        if direction.upper() in ["BUY", "LONG"]:
            direction_normalized = "BUY"
            if stop_rules.get("type") == "structure" and swing_low < entry_price:
                stop_loss = round(swing_low - (0.5 * atr), 5)
            else:
                stop_loss = round(entry_price - (atr * atr_multiplier), 5)

            if (entry_price - stop_loss) < (5 * pip_size):
                stop_loss = round(entry_price - (5 * pip_size), 5)

            sl_dist = max(entry_price - stop_loss, pip_size)
            sl_pips = round(sl_dist / pip_size, 1)

            if tp_fixed_rr:
                tp_dist = sl_dist * float(tp_fixed_rr)
            elif tp_rules.get("type") == "structure" and swing_high > entry_price:
                tp_dist = max(swing_high - entry_price, sl_dist * min_rr)
            else:
                tp_dist = atr * tp_atr_multiplier

            take_profit = round(entry_price + tp_dist, 5)
            tp_pips = round(tp_dist / pip_size, 1)
        else:
            direction_normalized = "SELL"
            if stop_rules.get("type") == "structure" and swing_high > entry_price:
                stop_loss = round(swing_high + (0.5 * atr), 5)
            else:
                stop_loss = round(entry_price + (atr * atr_multiplier), 5)

            if (stop_loss - entry_price) < (5 * pip_size):
                stop_loss = round(entry_price + (5 * pip_size), 5)

            sl_dist = max(stop_loss - entry_price, pip_size)
            sl_pips = round(sl_dist / pip_size, 1)

            if tp_fixed_rr:
                tp_dist = sl_dist * float(tp_fixed_rr)
            elif tp_rules.get("type") == "structure" and swing_low < entry_price:
                tp_dist = max(entry_price - swing_low, sl_dist * min_rr)
            else:
                tp_dist = atr * tp_atr_multiplier

            take_profit = round(entry_price - tp_dist, 5)
            tp_pips = round(tp_dist / pip_size, 1)

        rr_ratio = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 0.0
        is_valid_rr = rr_ratio >= min_rr

        # Canonical Position Sizing Call
        risk_req = RiskRequest(
            account_balance=account_balance,
            risk_percent=risk_percent,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit_1=take_profit,
            pip_size=pip_size,
            contract_size=contract_size,
            quote_currency=quote_cur,
            symbol=instrument.symbol
        )

        try:
            risk_result = calculate_position_size(risk_req, live_rates)
            position_size_lots = risk_result.position_size_lots
            risk_amount = risk_result.risk_amount_usd
        except Exception:
            pip_val = pip_size * contract_size
            risk_amount = account_balance * (risk_percent / 100.0)
            position_size_lots = round(risk_amount / (sl_pips * pip_val), 2) if sl_pips * pip_val > 0 else 0.01

        rejection_reason = None
        if not is_valid_rr:
            rejection_reason = f"Calculated RR {rr_ratio} is below strategy minimum {min_rr}"

        return TradeCalculationResult(
            direction=direction_normalized,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            stop_loss_pips=sl_pips,
            take_profit_pips=tp_pips,
            risk_reward_ratio=rr_ratio,
            position_size_lots=position_size_lots,
            risk_amount_usd=risk_amount,
            is_valid_rr=is_valid_rr,
            rejection_reason=rejection_reason
        )
