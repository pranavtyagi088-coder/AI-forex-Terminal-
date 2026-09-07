from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class MTFValidationResult:
    is_aligned: bool
    decision: str # VALIDATED, WAIT, NO_TRADE
    reasons: List[str]
    htf_regime: str
    mtf_regime: str
    ltf_regime: str

class MultiTimeframeValidator:
    """
    Module 5: Validates agreement across HTF (D1/4H), MTF (1H), and LTF (15M/5M).
    Disagreement leads to WAIT or NO_TRADE with explicit reason.
    """

    @staticmethod
    def validate(
        htf_state: Dict[str, Any],
        mtf_state: Dict[str, Any],
        ltf_state: Dict[str, Any],
        direction: str
    ) -> MTFValidationResult:
        reasons = []
        is_aligned = True
        decision = "VALIDATED"

        htf_regime = htf_state.get("regime", "RANGING")
        mtf_regime = mtf_state.get("regime", "RANGING")
        ltf_regime = ltf_state.get("regime", "RANGING")

        dir_upper = direction.upper()

        # HTF check (Directional trend filter)
        if dir_upper in ["BUY", "LONG"]:
            if "BEARISH" in htf_regime:
                is_aligned = False
                decision = "NO_TRADE"
                reasons.append(f"HTF trend conflict: HTF is {htf_regime}, opposing BUY direction.")
            elif htf_regime == "HIGH_VOLATILITY_UNCLEAR":
                is_aligned = False
                decision = "WAIT"
                reasons.append("HTF in extreme unclear volatility.")
        elif dir_upper in ["SELL", "SHORT"]:
            if "BULLISH" in htf_regime:
                is_aligned = False
                decision = "NO_TRADE"
                reasons.append(f"HTF trend conflict: HTF is {htf_regime}, opposing SELL direction.")
            elif htf_regime == "HIGH_VOLATILITY_UNCLEAR":
                is_aligned = False
                decision = "WAIT"
                reasons.append("HTF in extreme unclear volatility.")

        # MTF check (Setup structure)
        if mtf_state.get("is_choppy", False):
            if decision != "NO_TRADE":
                decision = "WAIT"
            reasons.append("MTF setup is choppy/unclear structure.")

        # LTF check (Trigger condition)
        ltf_rsi = ltf_state.get("rsi", 50.0)
        if dir_upper in ["BUY", "LONG"] and ltf_rsi > 75.0:
            if decision != "NO_TRADE":
                decision = "WAIT"
            reasons.append(f"LTF entry overextended: 15M RSI {ltf_rsi:.1f} > 75 (Wait for pullback).")
        elif dir_upper in ["SELL", "SHORT"] and ltf_rsi < 25.0:
            if decision != "NO_TRADE":
                decision = "WAIT"
            reasons.append(f"LTF entry overextended: 15M RSI {ltf_rsi:.1f} < 25 (Wait for bounce).")

        if reasons and decision == "VALIDATED":
            decision = "WAIT"
            is_aligned = False

        if not reasons:
            reasons.append("All timeframes (HTF/MTF/LTF) aligned with trade direction.")

        return MTFValidationResult(
            is_aligned=(decision == "VALIDATED"),
            decision=decision,
            reasons=reasons,
            htf_regime=htf_regime,
            mtf_regime=mtf_regime,
            ltf_regime=ltf_regime
        )
