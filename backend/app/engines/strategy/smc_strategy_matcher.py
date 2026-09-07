"""
SMC Strategy Matcher — Deterministic strategy matching using Structure + Liquidity
data. Integrates decay adjustments. AI opinion is NOT used for strategy selection.

Architecture:
  Market State + Structure + Liquidity
       |
  Deterministic Condition Checker (this module)
       |
  Decay Adjustment (from DecayDetector)
       |
  Final Ranked Output
       |
  Safety Gate -> Risk -> No-Trade (existing pipeline)
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from app.engines.strategy.strategy_registry import get_builtin_strategies
from app.engines.strategy.decay_detector import DecayDetector


@dataclass
class StrategyMatchResult:
    strategy_id: str
    name: str
    base_match_score: float
    decay_status: str
    decay_adjustment: float
    final_strategy_score: float
    matched_conditions: List[str]
    missing_conditions: List[str]
    conflicting_conditions: List[str]
    recommendation: str  # BEST_MATCH, SUITABLE, WEAK, REJECTED, NO_CONFIDENT_STRATEGY
    rejection_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "name": self.name,
            "base_match_score": self.base_match_score,
            "decay_status": self.decay_status,
            "decay_adjustment": self.decay_adjustment,
            "final_strategy_score": self.final_strategy_score,
            "matched_conditions": self.matched_conditions,
            "missing_conditions": self.missing_conditions,
            "conflicting_conditions": self.conflicting_conditions,
            "recommendation": self.recommendation,
            "rejection_reason": self.rejection_reason
        }


DECAY_PENALTIES = {
    "ACTIVE": 0.0,
    "HEALTHY": 0.0,
    "CAUTION": -8.0,
    "WATCH": -8.0,
    "DEGRADED": -20.0,
    "RETIRED": -100.0,
    "SUSPENDED": -100.0,
    "UNKNOWN": 0.0
}


def _check_structure_conditions(
    rules: Dict[str, Any],
    structure_data: Dict[str, Any],
    direction: str
) -> tuple:
    matched = []
    missing = []
    conflicting = []

    struct_req = rules.get("structure_requirements", {})

    if struct_req.get("bos_or_choch", False):
        bos = structure_data.get("bos_detected", False)
        choch = structure_data.get("choch_detected", False)
        if bos or choch:
            event = structure_data.get("last_event", "BOS")
            matched.append(f"Structure break confirmed ({event})")
        else:
            missing.append("No BOS or CHoCH detected")

    if struct_req.get("structure_bias_match", False):
        bias = structure_data.get("structure_bias", "NEUTRAL").upper()
        direction_upper = direction.upper()
        if direction_upper == "BUY" and bias in ["BULLISH", "BULLISH_REVERSAL"]:
            matched.append(f"Bullish structure bias aligns with BUY")
        elif direction_upper == "SELL" and bias in ["BEARISH", "BEARISH_REVERSAL"]:
            matched.append(f"Bearish structure bias aligns with SELL")
        elif bias == "NEUTRAL":
            missing.append("Structure bias is NEUTRAL (no clear alignment)")
        else:
            conflicting.append(f"Structure bias ({bias}) conflicts with direction ({direction_upper})")

    return matched, missing, conflicting


def _check_liquidity_conditions(
    rules: Dict[str, Any],
    liquidity_data: Dict[str, Any],
    direction: str
) -> tuple:
    matched = []
    missing = []
    conflicting = []

    liq_req = rules.get("liquidity_requirements", {})

    if liq_req.get("fvg_required", False):
        fvg_dir = liq_req.get("fvg_direction", "aligned")
        direction_upper = direction.upper()

        if fvg_dir == "aligned":
            if direction_upper == "BUY":
                count = liquidity_data.get("bullish_fvg_open", 0)
                if count > 0:
                    matched.append(f"Bullish FVG present ({count} open)")
                else:
                    missing.append("No aligned (bullish) FVG detected")
            else:
                count = liquidity_data.get("bearish_fvg_open", 0)
                if count > 0:
                    matched.append(f"Bearish FVG present ({count} open)")
                else:
                    missing.append("No aligned (bearish) FVG detected")
        else:
            total = liquidity_data.get("unmitigated_fvg_count", 0)
            if total > 0:
                matched.append(f"FVG present ({total} unmitigated)")
            else:
                missing.append("No FVG detected")

    if liq_req.get("sweep_required", False):
        total_fvgs = liquidity_data.get("total_fvg_count", 0)
        unmitigated = liquidity_data.get("unmitigated_fvg_count", 0)
        if unmitigated > 0:
            matched.append("Liquidity interaction detected (unmitigated FVGs imply sweep activity)")
        else:
            missing.append("No liquidity sweep evidence detected")

    return matched, missing, conflicting


def _check_market_conditions(
    rules: Dict[str, Any],
    market_state: Dict[str, Any]
) -> tuple:
    matched = []
    missing = []
    conflicting = []

    regime = market_state.get("regime", "UNKNOWN").upper()
    allowed_regimes = [r.upper() for r in rules.get("market_regimes", ["ANY"])]

    if "ANY" in allowed_regimes or regime in allowed_regimes:
        matched.append(f"Regime '{regime}' is compatible")
    else:
        conflicting.append(f"Regime '{regime}' not in allowed {allowed_regimes}")

    session = market_state.get("session", market_state.get("active_session", "UNKNOWN")).upper()
    allowed_sessions = [s.upper() for s in rules.get("sessions", ["ANY"])]

    if "ANY" in allowed_sessions or session in allowed_sessions:
        matched.append(f"Session '{session}' is valid")
    else:
        missing.append(f"Session '{session}' not optimal (needs {allowed_sessions})")

    vol_filters = rules.get("volatility_filters", {})
    atr_pct = market_state.get("volatility_percentile", market_state.get("atr", 0.0015) * 10000)
    min_vol = vol_filters.get("min_atr_percentile", 0)
    max_vol = vol_filters.get("max_atr_percentile", 100)

    if min_vol <= atr_pct <= max_vol:
        matched.append(f"Volatility acceptable ({atr_pct:.1f}th percentile)")
    elif atr_pct > max_vol:
        conflicting.append(f"Volatility too high ({atr_pct:.1f}% > {max_vol}% ceiling)")
    else:
        missing.append(f"Volatility too low ({atr_pct:.1f}% < {min_vol}% floor)")

    return matched, missing, conflicting


def match_single_strategy(
    strategy: Dict[str, Any],
    market_state: Dict[str, Any],
    structure_data: Dict[str, Any],
    liquidity_data: Dict[str, Any],
    direction: str,
    decay_status: str = "ACTIVE"
) -> StrategyMatchResult:
    rules = strategy.get("rules", {})
    sid = strategy.get("strategy_id", "UNKNOWN")
    name = strategy.get("name", "Unnamed")

    all_matched = []
    all_missing = []
    all_conflicting = []

    m1, mi1, c1 = _check_market_conditions(rules, market_state)
    m2, mi2, c2 = _check_structure_conditions(rules, structure_data, direction)
    m3, mi3, c3 = _check_liquidity_conditions(rules, liquidity_data, direction)

    all_matched = m1 + m2 + m3
    all_missing = mi1 + mi2 + mi3
    all_conflicting = c1 + c2 + c3

    required = rules.get("required_confirmations", 3)
    total_conditions = required + len(all_missing) + len(all_conflicting)
    if total_conditions == 0:
        total_conditions = 1

    base_score = min(100.0, (len(all_matched) / max(total_conditions, 1)) * 100.0)

    if all_conflicting:
        base_score = max(0.0, base_score - (len(all_conflicting) * 15.0))

    decay_adj = DECAY_PENALTIES.get(decay_status.upper(), 0.0)
    final_score = max(0.0, min(100.0, base_score + decay_adj))

    if len(all_conflicting) >= 2 or final_score < 25.0:
        recommendation = "REJECTED"
        rejection = "; ".join(all_conflicting + all_missing[:2]) if all_conflicting else "Insufficient conditions"
    elif final_score >= 75.0 and len(all_missing) <= 1:
        recommendation = "BEST_MATCH"
        rejection = ""
    elif final_score >= 55.0:
        recommendation = "SUITABLE"
        rejection = ""
    elif final_score >= 35.0:
        recommendation = "WEAK"
        rejection = "; ".join(all_missing[:2])
    else:
        recommendation = "REJECTED"
        rejection = "; ".join(all_conflicting + all_missing[:2]) if (all_conflicting or all_missing) else "Score below threshold"

    return StrategyMatchResult(
        strategy_id=sid,
        name=name,
        base_match_score=round(base_score, 1),
        decay_status=decay_status.upper(),
        decay_adjustment=decay_adj,
        final_strategy_score=round(final_score, 1),
        matched_conditions=all_matched,
        missing_conditions=all_missing,
        conflicting_conditions=all_conflicting,
        recommendation=recommendation,
        rejection_reason=rejection
    )


def rank_all_strategies(
    market_state: Dict[str, Any],
    structure_data: Dict[str, Any],
    liquidity_data: Dict[str, Any],
    direction: str,
    decay_map: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    strategies = get_builtin_strategies()
    if decay_map is None:
        decay_map = {}

    results = []
    for strat in strategies:
        sid = strat.get("strategy_id", "")
        decay_status = decay_map.get(sid, strat.get("lifecycle_status", "ACTIVE"))
        result = match_single_strategy(
            strategy=strat,
            market_state=market_state,
            structure_data=structure_data,
            liquidity_data=liquidity_data,
            direction=direction,
            decay_status=decay_status
        )
        results.append(result)

    results.sort(key=lambda r: r.final_strategy_score, reverse=True)

    best = None
    for r in results:
        if r.recommendation in ["BEST_MATCH", "SUITABLE"]:
            best = r
            break

    return {
        "best_strategy": best.to_dict() if best else None,
        "strategy_ranking": [r.to_dict() for r in results],
        "best_strategy_name": best.name if best else "NO_CONFIDENT_STRATEGY",
        "best_strategy_score": best.final_strategy_score if best else 0.0,
        "best_strategy_reasons": best.matched_conditions if best else [],
        "evaluated_count": len(results)
    }
