"""
Strategy Matching Engine - Module 2 of Strategy Engine.
Scores each strategy against current market state.
Evidence-quality cap applied per Invariant B.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.engines.strategy.market_state import MarketState


@dataclass
class MatchScore:
    strategy_id: str
    strategy_name: str
    instrument: str
    evidence_level: str
    components: dict[str, float] = field(default_factory=dict)
    raw_total: float = 0.0
    evidence_cap: int = 100
    final_score: float = 0.0
    why_bullets: list[str] = field(default_factory=list)


# Evidence cap per level (Invariant B)
EVIDENCE_CAPS = {"A": 100, "B": 85, "C": 60, "D": 35}

# Session adjacency map
SESSION_ADJACENT = {
    "SYDNEY": ["TOKYO"],
    "TOKYO": ["SYDNEY", "LONDON"],
    "LONDON": ["TOKYO", "LONDON_NY_OVERLAP"],
    "LONDON_NY_OVERLAP": ["LONDON", "NEW_YORK"],
    "NEW_YORK": ["LONDON_NY_OVERLAP"],
}


def _score_regime_fit(state: MarketState, strategy_regimes: list[str]) -> tuple[float, str]:
    """20 points max."""
    if state.regime in strategy_regimes:
        return 20.0, f"Regime {state.regime} matches strategy"
    if "ANY" in strategy_regimes:
        return 15.0, f"Strategy accepts any regime"
    return 0.0, f"Regime {state.regime} does not match {strategy_regimes}"


def _score_volatility_fit(state: MarketState, strategy_data: dict) -> tuple[float, str]:
    """15 points max."""
    vol_filters = strategy_data.get("volatility_filters", {})

    max_atr = vol_filters.get("max_atr_percentile", vol_filters.get("max_atr_percentile_entry", 100))

    if state.volatility_pct <= max_atr:
        return 15.0, f"Volatility {state.volatility_pct:.0f}th pctile within tolerance"

    if state.volatility_pct <= max_atr + 10:
        return 8.0, f"Volatility slightly elevated ({state.volatility_pct:.0f}th)"

    return 0.0, f"Volatility {state.volatility_pct:.0f}th exceeds max {max_atr}"


def _score_session_fit(state: MarketState, strategy_sessions: list[str]) -> tuple[float, str]:
    """10 points max."""
    if "ANY" in strategy_sessions or "N/A" in strategy_sessions:
        return 10.0, "Strategy is not session-specific"
    if state.session in strategy_sessions:
        return 10.0, f"Session {state.session} matches"
    adjacent = SESSION_ADJACENT.get(state.session, [])
    if any(s in adjacent for s in strategy_sessions):
        return 5.0, f"Session {state.session} adjacent to preferred"
    return 0.0, f"Session {state.session} not preferred"


def _score_structure_fit(state: MarketState, strategy_type: str) -> tuple[float, str]:
    """15 points max."""
    if not state.structure_confirmed:
        return 5.0, "Structure not confirmed - partial credit"

    # Check if structure agrees with strategy direction
    if strategy_type in ("momentum", "trend_following"):
        if state.structure_bias in ("bullish", "bearish"):
            return 15.0, f"Confirmed {state.structure_bias} structure supports trend strategy"
        return 8.0, "Structure confirmed but unclear bias"

    if strategy_type in ("carry_macro", "statistical_macro", "statistical_macro_filter"):
        return 10.0, "Structure noted but less critical for macro strategy"

    if strategy_type in ("volatility_event_driven", "event_driven_macro", "event_driven_mean_reversion"):
        return 10.0, "Event-driven strategy - structure secondary"

    return 8.0, "Structure partially aligned"


def _score_momentum_fit(state: MarketState, strategy_type: str) -> tuple[float, str]:
    """10 points max."""
    if strategy_type in ("momentum", "trend_following"):
        if state.momentum_direction in ("bullish", "bearish"):
            return 10.0, f"Clear {state.momentum_direction} momentum supports strategy"
        return 3.0, "Neutral momentum - weak support for trend strategy"

    if strategy_type in ("volatility_event_driven", "event_driven_mean_reversion"):
        return 7.0, "Momentum less critical for event-driven strategy"

    return 5.0, "Momentum noted"


def _score_news_fit(state: MarketState) -> tuple[float, str]:
    """15 points max."""
    if state.news_risk == "high":
        return 0.0, "High news risk - avoid"
    if state.news_risk == "medium":
        return 8.0, "Medium news risk - partial caution"
    return 15.0, "No significant news risk"


def score_strategy(
    strategy_data: dict,
    state: MarketState,
) -> MatchScore:
    """Score a strategy against the current market state.
    Returns a MatchScore with component breakdown and evidence-capped final score."""

    components = {}
    why = []

    # 1. Regime fit (20 pts)
    regimes = strategy_data.get("market_regimes", ["ANY"])
    score, reason = _score_regime_fit(state, regimes)
    components["regime_fit"] = score
    why.append(f"Regime: {reason} ({score:.0f}/20)")

    # 2. Volatility fit (15 pts)
    score, reason = _score_volatility_fit(state, strategy_data)
    components["volatility_fit"] = score
    why.append(f"Volatility: {reason} ({score:.0f}/15)")

    # 3. Session fit (10 pts)
    sessions = strategy_data.get("sessions", ["ANY"])
    score, reason = _score_session_fit(state, sessions)
    components["session_fit"] = score
    why.append(f"Session: {reason} ({score:.0f}/10)")

    # 4. News fit (15 pts)
    score, reason = _score_news_fit(state)
    components["news_fit"] = score
    why.append(f"News: {reason} ({score:.0f}/15)")

    # 5. Structure fit (15 pts)
    strategy_type = strategy_data.get("strategy_type", "unknown")
    score, reason = _score_structure_fit(state, strategy_type)
    components["structure_fit"] = score
    why.append(f"Structure: {reason} ({score:.0f}/15)")

    # 6. Momentum fit (10 pts)
    score, reason = _score_momentum_fit(state, strategy_type)
    components["momentum_fit"] = score
    why.append(f"Momentum: {reason} ({score:.0f}/10)")

    # 7. Pair fit (10 pts - static from strategy)
    pair_fit = 8.0  # Default for strategies in this library
    components["pair_fit"] = pair_fit

    # 8. RR fit (5 pts - computed after trade calculation, placeholder)
    components["rr_fit"] = 0.0  # Filled by caller after trade calc

    raw_total = sum(components.values())

    # Evidence cap (Invariant B)
    evidence_level = strategy_data.get("evidence_level", "C")
    # Handle compound levels like "A/B"
    primary_level = evidence_level[0] if evidence_level else "C"
    evidence_cap = EVIDENCE_CAPS.get(primary_level, 60)

    final_score = min(raw_total, evidence_cap)

    return MatchScore(
        strategy_id=strategy_data.get("strategy_id", "unknown"),
        strategy_name=strategy_data.get("strategy_name", "Unknown"),
        instrument=strategy_data.get("instrument", state.instrument),
        evidence_level=evidence_level,
        components=components,
        raw_total=round(raw_total, 1),
        evidence_cap=evidence_cap,
        final_score=round(final_score, 1),
        why_bullets=why,
    )


def rank_strategies(
    strategies: list[dict],
    state: MarketState,
    include_experimental: bool = False,
) -> list[MatchScore]:
    """Score, filter, and rank all candidate strategies."""
    scored = []

    for s in strategies:
        # Filter by instrument
        if s.get("instrument") != state.instrument:
            continue

        # Evidence gate (Invariant B)
        evidence_level = s.get("evidence_level", "C")
        primary_level = evidence_level[0] if evidence_level else "C"

        if primary_level in ("A", "B"):
            pass  # Always surfaceable
        elif primary_level == "C" and include_experimental:
            pass  # User opted in
        else:
            if primary_level in ("C", "D"):
                continue  # Skip

        ms = score_strategy(s, state)
        scored.append(ms)

    # Sort by evidence-capped final score, descending
    scored.sort(key=lambda m: m.final_score, reverse=True)
    return scored
