from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from app.engines.strategy.mtf_validator import MTFValidationResult
from app.engines.strategy.trade_calculator import TradeCalculationResult

@dataclass
class SafetyGateResult:
    decision: str # TRADE, WAIT, NO_TRADE
    is_safe: bool
    blocking_reasons: List[str]

class SafetyNoTradeGate:
    """
    Module 6: Final deterministic safety gate evaluating news,
    volatility, spread, HTF alignment, and invalidation rules.
    """

    @staticmethod
    def evaluate(
        market_state: Dict[str, Any],
        mtf_result: MTFValidationResult,
        trade_calc: TradeCalculationResult,
        news_items: Optional[List[Dict[str, Any]]] = None,
        spread_pips: float = 1.0,
        max_allowed_spread_pips: float = 3.5
    ) -> SafetyGateResult:
        blocking_reasons = []
        decision = "TRADE"

        # 1. Check MTF Validator decision
        if mtf_result.decision == "NO_TRADE":
            decision = "NO_TRADE"
            blocking_reasons.extend(mtf_result.reasons)
        elif mtf_result.decision == "WAIT":
            if decision != "NO_TRADE":
                decision = "WAIT"
            blocking_reasons.extend(mtf_result.reasons)

        # 2. Check RR Ratio Validity
        if not trade_calc.is_valid_rr and trade_calc.rejection_reason:
            decision = "NO_TRADE"
            blocking_reasons.append(trade_calc.rejection_reason)

        # 3. Spread Check
        if spread_pips > max_allowed_spread_pips:
            if decision != "NO_TRADE":
                decision = "WAIT"
            blocking_reasons.append(
                f"Spread too wide: {spread_pips} pips exceeds max threshold {max_allowed_spread_pips} pips."
            )

        # 4. Volatility Spike Check
        volatility_pct = market_state.get("volatility_percentile", 50.0)
        if volatility_pct >= 95.0:
            decision = "NO_TRADE"
            blocking_reasons.append(
                f"Extreme volatility spike: ATR percentile {volatility_pct:.1f}% >= 95.0%."
            )

        # 5. News Event Check (High Impact Avoidance)
        if news_items:
            for item in news_items:
                impact = item.get("impact", "").upper()
                if impact == "HIGH":
                    # If high impact news is breaking or imminent
                    if decision != "NO_TRADE":
                        decision = "WAIT"
                    blocking_reasons.append(
                        f"High-impact news event active: {item.get('title', 'Macro Event')}."
                    )
                    break

        is_safe = (decision == "TRADE")
        if is_safe and not blocking_reasons:
            blocking_reasons.append("Safety gate passed: all risk checks within operational thresholds.")

        return SafetyGateResult(
            decision=decision,
            is_safe=is_safe,
            blocking_reasons=blocking_reasons
        )
