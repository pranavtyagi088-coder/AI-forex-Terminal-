from typing import List, Dict, Optional
import math
from pydantic import BaseModel, Field
from app.engines.risk.correlation import CorrelationRiskEngine, OpenPositionInput, AggregateRiskResult


class PreFlightTradeRequest(BaseModel):
    symbol: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit: Optional[float] = Field(None, gt=0)
    account_balance: float = Field(..., gt=0)
    account_equity: Optional[float] = None
    open_positions: List[OpenPositionInput] = Field(default_factory=list)
    risk_per_trade_pct: float = Field(1.0, gt=0, le=10.0)
    circuit_breaker_state: str = "NORMAL"
    current_daily_loss_pct: float = 0.0
    current_total_drawdown_pct: float = 0.0
    max_daily_loss_pct: float = 5.0
    max_total_drawdown_pct: float = 10.0
    is_news_blackout: bool = False
    allow_news_trading: bool = False
    is_weekend_window: bool = False
    allow_weekend_holding: bool = False
    quotes: Dict[str, float] = Field(default_factory=dict)
    min_lot: float = 0.01
    max_lot: float = 100.0
    lot_step: float = 0.01


class PreFlightTradeResponse(BaseModel):
    allowed: bool
    approved_lot_size: float
    risk_amount_usd: float
    risk_pct: float
    pip_risk: float
    reward_risk_ratio: Optional[float] = None
    rejection_reasons: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    gate_checks: Dict[str, bool] = Field(default_factory=dict)


class PreFlightGatekeeper:
    def __init__(self, correlation_engine: Optional[CorrelationRiskEngine] = None):
        self.correlation_engine = correlation_engine or CorrelationRiskEngine()

    def _calculate_pip_value(self, symbol: str, entry_price: float, quotes: Dict[str, float]) -> float:
        s = symbol.upper()
        if s.endswith("USD") and not s.startswith("XAU"):
            return 10.0
        elif s in ("XAUUSD", "GOLD"):
            return 10.0
        elif s.startswith("USD"):
            rate = quotes.get(s, entry_price)
            pip_unit = 0.01 if s.endswith("JPY") else 0.0001
            return (100000.0 * pip_unit) / rate
        elif s == "EURGBP":
            gbpusd = quotes.get("GBPUSD", 1.25)
            return 10.0 * gbpusd
        elif s.endswith("JPY"):
            usdjpy = quotes.get("USDJPY", 150.0)
            return (100000.0 * 0.01) / usdjpy
        return 10.0

    def evaluate(self, req: PreFlightTradeRequest) -> PreFlightTradeResponse:
        rejection_reasons: List[str] = []
        warnings: List[str] = []
        gate_checks = {
            "circuit_breaker": True,
            "prop_firm_drawdown": True,
            "news_and_calendar": True,
            "stop_loss_geometry": True,
            "portfolio_correlation": True,
        }

        if req.circuit_breaker_state == "KILL_SWITCH":
            rejection_reasons.append("Circuit Breaker KILL_SWITCH is active. Trading halted.")
            gate_checks["circuit_breaker"] = False
        elif req.circuit_breaker_state == "RESTRICTED":
            warnings.append("Circuit Breaker RESTRICTED mode active. Reduce risk.")

        if req.current_daily_loss_pct >= req.max_daily_loss_pct:
            rejection_reasons.append(
                f"Daily drawdown limit reached ({req.current_daily_loss_pct:.2f}% >= {req.max_daily_loss_pct:.2f}%)."
            )
            gate_checks["prop_firm_drawdown"] = False

        if req.current_total_drawdown_pct >= req.max_total_drawdown_pct:
            rejection_reasons.append(
                f"Max drawdown limit breached ({req.current_total_drawdown_pct:.2f}% >= {req.max_total_drawdown_pct:.2f}%)."
            )
            gate_checks["prop_firm_drawdown"] = False

        if req.is_news_blackout and not req.allow_news_trading:
            rejection_reasons.append("High-impact news blackout window is active for this prop firm challenge.")
            gate_checks["news_and_calendar"] = False

        if req.is_weekend_window and not req.allow_weekend_holding:
            warnings.append("Weekend rollover approaching. Firm mandates closing before weekend.")

        sym = req.symbol.upper()
        pip_unit = 0.01 if sym.endswith("JPY") else 0.0001
        if sym in ("XAUUSD", "GOLD"):
            pip_unit = 0.1

        price_diff = req.entry_price - req.stop_loss if req.direction == "BUY" else req.stop_loss - req.entry_price
        if price_diff <= 0:
            rejection_reasons.append(
                f"Invalid Stop Loss geometry: {req.direction} requires SL {'below' if req.direction == 'BUY' else 'above'} entry."
            )
            gate_checks["stop_loss_geometry"] = False
            pip_distance = 0.0
        else:
            pip_distance = price_diff / pip_unit

        risk_usd = req.account_balance * (req.risk_per_trade_pct / 100.0)

        rr_ratio: Optional[float] = None
        if req.take_profit and price_diff > 0:
            target_diff = req.take_profit - req.entry_price if req.direction == "BUY" else req.entry_price - req.take_profit
            if target_diff > 0:
                rr_ratio = round(target_diff / price_diff, 2)
                if rr_ratio < 1.0:
                    warnings.append(f"Sub-optimal Risk-to-Reward ratio: {rr_ratio}:1 (Recommended >= 1.5:1)")
            else:
                warnings.append("Take profit is set on wrong side of entry price.")

        approved_lot = 0.0
        if pip_distance > 0:
            pip_val = self._calculate_pip_value(req.symbol, req.entry_price, req.quotes)
            raw_lot = risk_usd / (pip_distance * pip_val)
            stepped_lot = math.floor(raw_lot / req.lot_step) * req.lot_step
            approved_lot = max(req.min_lot, min(stepped_lot, req.max_lot))
            approved_lot = round(approved_lot, 2)

        corr_result: AggregateRiskResult = self.correlation_engine.evaluate_aggregate_risk(
            account_balance=req.account_balance,
            open_positions=req.open_positions,
            proposed_symbol=req.symbol,
            proposed_direction=req.direction,
            proposed_risk_usd=risk_usd,
            proposed_risk_pct=req.risk_per_trade_pct,

        )

        if not corr_result.allowed:
            rejection_reasons.extend(corr_result.violations)
            gate_checks["portfolio_correlation"] = False

        warnings.extend(corr_result.warnings)

        allowed = len(rejection_reasons) == 0 and approved_lot > 0

        return PreFlightTradeResponse(
            allowed=allowed,
            approved_lot_size=approved_lot if allowed else 0.0,
            risk_amount_usd=risk_usd,
            risk_pct=req.risk_per_trade_pct,
            pip_risk=round(pip_distance, 1),
            reward_risk_ratio=rr_ratio,
            rejection_reasons=rejection_reasons,
            warnings=warnings,
            gate_checks=gate_checks,
        )
