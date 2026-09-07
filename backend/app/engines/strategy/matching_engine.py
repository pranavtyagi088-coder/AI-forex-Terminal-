import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional, Union
from app.models.strategy import Strategy
from app.engines.indicators.technical import TechnicalSnapshot

EVIDENCE_GRADE_CAPS = {
    "A": 100.0,
    "B": 85.0,
    "C": 60.0,
    "D": 35.0
}

@dataclass
class MatchScore:
    strategy_id: str
    name: str
    evidence_grade: str
    lifecycle_status: str
    match_score: float
    raw_score: float
    score_breakdown: Dict[str, float]
    why_bullets: List[str]
    rules: Dict[str, Any]

    @property
    def score(self) -> float:
        return self.match_score

    @property
    def final_score(self) -> float:
        return self.match_score

    @property
    def strategy_name(self) -> str:
        return self.name

    @property
    def breakdown(self) -> Dict[str, float]:
        return self.score_breakdown

    @property
    def evidence_cap(self) -> float:
        # Match case-insensitive Grade to cap
        grade = self.evidence_grade.upper() if self.evidence_grade else "D"
        return EVIDENCE_GRADE_CAPS.get(grade, 35.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name": self.name,
            "name": self.name,
            "evidence_grade": self.evidence_grade,
            "lifecycle_status": self.lifecycle_status,
            "match_score": self.match_score,
            "score": self.match_score,
            "final_score": self.match_score,
            "raw_score": self.raw_score,
            "score_breakdown": self.score_breakdown,
            "breakdown": self.score_breakdown,
            "why_bullets": self.why_bullets,
            "rules": self.rules,
            "evidence_cap": self.evidence_cap
        }

def _extract_strategy_meta(strategy: Any) -> Dict[str, Any]:
    """Unified parser for Strategy ORM objects and dict data types."""
    if isinstance(strategy, dict):
        rules = strategy.get("rules", strategy)
        grade = strategy.get("evidence_grade") or strategy.get("evidence_level") or "D"
        name = strategy.get("strategy_name") or strategy.get("name") or "Unnamed"
        sid = strategy.get("strategy_id") or strategy.get("id") or "unknown"
        status = strategy.get("lifecycle_status", "ACTIVE")
        if not isinstance(rules, dict) or "market_regimes" not in rules:
            rules = {
                "market_regimes": strategy.get("market_regimes", ["ANY"]),
                "sessions": strategy.get("sessions", ["ANY"]),
                "volatility_filters": strategy.get("volatility_filters", {}),
                "min_acceptable_rr": strategy.get("min_acceptable_rr", 1.5)
            }
    else:
        rules = strategy.rules if hasattr(strategy, "rules") and strategy.rules else {}
        if isinstance(rules, str):
            try:
                rules = json.loads(rules)
            except Exception:
                rules = {}
        grade = getattr(strategy, "evidence_grade", "D") or "D"
        name = getattr(strategy, "name", "Unnamed")
        sid = str(getattr(strategy, "id", "unknown"))
        status = getattr(strategy, "lifecycle_status", "ACTIVE")

    return {
        "rules": rules,
        "grade": str(grade).upper(),
        "name": name,
        "id": str(sid),
        "status": status
    }

def _extract_state_fields(market_state_or_snap: Any) -> Dict[str, Any]:
    if isinstance(market_state_or_snap, TechnicalSnapshot):
        regime = "TRENDING_BULLISH" if market_state_or_snap.trend_direction == "bullish" else ("TRENDING_BEARISH" if market_state_or_snap.trend_direction == "bearish" else "RANGING")
        return {
            "regime": regime,
            "volatility_percentile": market_state_or_snap.atr_pct * 100.0,
            "session": "LONDON",
            "structure_confirmed": market_state_or_snap.structure_confirmed,
            "adx": market_state_or_snap.trend_strength
        }
    if isinstance(market_state_or_snap, dict):
        return {
            "regime": market_state_or_snap.get("regime", "RANGING"),
            "volatility_percentile": market_state_or_snap.get("volatility_percentile", 50.0),
            "session": market_state_or_snap.get("session", "LONDON"),
            "structure_confirmed": market_state_or_snap.get("structure_confirmed", True),
            "adx": market_state_or_snap.get("adx", 25.0)
        }
    return {
        "regime": getattr(market_state_or_snap, "regime", "RANGING"),
        "volatility_percentile": getattr(market_state_or_snap, "volatility_percentile", 50.0),
        "session": getattr(market_state_or_snap, "session", "LONDON"),
        "structure_confirmed": getattr(market_state_or_snap, "structure_confirmed", True),
        "adx": getattr(market_state_or_snap, "adx", 25.0)
    }

def score_strategy(strategy: Any, market_state_or_snap: Any) -> MatchScore:
    meta = _extract_strategy_meta(strategy)
    state = _extract_state_fields(market_state_or_snap)

    rules = meta["rules"]

    breakdown = {
        "regime_fit": 0.0,
        "volatility_fit": 0.0,
        "session_fit": 0.0,
        "news_fit": 15.0,
        "structure_fit": 0.0,
        "momentum_fit": 0.0,
        "pair_fit": 10.0,
        "rr_fit": 5.0
    }
    why_bullets = []

    allowed_regimes = rules.get("market_regimes", ["ANY"])
    if "ANY" in allowed_regimes or state["regime"] in allowed_regimes:
        breakdown["regime_fit"] = 20.0
        why_bullets.append(f"Market regime '{state['regime']}' directly aligns with strategy requirements.")
    else:
        breakdown["regime_fit"] = 5.0

    vol_filters = rules.get("volatility_filters", {})
    max_atr_pct = vol_filters.get("max_atr_percentile", 90.0)
    if state["volatility_percentile"] <= max_atr_pct:
        breakdown["volatility_fit"] = 15.0
        why_bullets.append(f"ATR volatility percentile ({state['volatility_percentile']:.1f}%) within ceiling ({max_atr_pct}%).")

    allowed_sessions = rules.get("sessions", ["ANY"])
    if "ANY" in allowed_sessions or "N/A" in allowed_sessions or state["session"] in allowed_sessions:
        breakdown["session_fit"] = 10.0
        why_bullets.append(f"Active session '{state['session']}' provides target liquidity.")
    else:
        breakdown["session_fit"] = 3.0

    if state["structure_confirmed"]:
        breakdown["structure_fit"] = 15.0
        why_bullets.append("Key swing structure confirmed.")
    else:
        breakdown["structure_fit"] = 5.0

    if state["adx"] >= 20.0:
        breakdown["momentum_fit"] = 10.0
        why_bullets.append(f"ADX momentum at {state['adx']:.1f} confirms directional participation.")
    else:
        breakdown["momentum_fit"] = 5.0

    raw_score = sum(breakdown.values())
    cap = EVIDENCE_GRADE_CAPS.get(meta["grade"], 35.0)
    capped_score = min(raw_score, cap)

    return MatchScore(
        strategy_id=meta["id"],
        name=meta["name"],
        evidence_grade=meta["grade"],
        lifecycle_status=meta["status"],
        match_score=round(capped_score, 2),
        raw_score=round(raw_score, 2),
        score_breakdown=breakdown,
        why_bullets=why_bullets,
        rules=rules
    )

def rank_strategies(
    strategies: List[Any],
    market_state: Any,
    user_opt_in_grade_c: bool = False
) -> List[Dict[str, Any]]:
    scored_list: List[MatchScore] = []
    for strat in strategies:
        meta = _extract_strategy_meta(strat)
        grade = meta["grade"]
        if grade == "D":
            continue
        if grade == "C" and not user_opt_in_grade_c:
            continue
        scored = score_strategy(strat, market_state)
        scored_list.append(scored)

    scored_list.sort(key=lambda s: s.match_score, reverse=True)
    return [s.to_dict() for s in scored_list[:3]]

class StrategyMatchingEngine:
    @staticmethod
    def score_strategy(strategy: Any, market_state: Any) -> MatchScore:
        return score_strategy(strategy, market_state)

    @staticmethod
    def rank_strategies(
        strategies: List[Any],
        market_state: Any,
        user_opt_in_grade_c: bool = False
    ) -> List[Dict[str, Any]]:
        return rank_strategies(strategies, market_state, user_opt_in_grade_c)

MatchingEngine = StrategyMatchingEngine
ScoredStrategy = MatchScore
