"""
Strategy Registry — Centralized repository of built-in institutional strategies.
Each strategy has deterministic conditions that reference market state, structure,
and liquidity data. AI opinion is NOT used for strategy selection.
"""

from typing import Dict, Any, List

BUILTIN_STRATEGIES: List[Dict[str, Any]] = [
    {
        "strategy_id": "LIQ_SWEEP_CONTINUATION",
        "name": "Liquidity Sweep Continuation",
        "description": "Enters after institutional liquidity raid (stop hunt) with displacement and FVG confirmation in direction of structural bias.",
        "evidence_grade": "A",
        "lifecycle_status": "ACTIVE",
        "rules": {
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "sessions": ["LONDON", "NEW_YORK"],
            "preferred_timeframes": ["5m", "15m", "1h"],
            "volatility_filters": {"min_atr_percentile": 20.0, "max_atr_percentile": 85.0},
            "min_acceptable_rr": 2.0,
            "structure_requirements": {
                "bos_or_choch": True,
                "structure_bias_match": True
            },
            "liquidity_requirements": {
                "sweep_required": True,
                "sweep_direction": "opposing",
                "fvg_required": True,
                "fvg_direction": "aligned"
            },
            "entry_conditions": [
                "Liquidity sweep of opposing side confirmed",
                "Displacement candle in structural direction",
                "Unmitigated FVG aligned with bias",
                "BOS or CHoCH in structural direction"
            ],
            "invalidation_conditions": [
                "Opposing BOS after entry",
                "Price closes beyond sweep wick against position"
            ],
            "contraindications": [
                "RANGING regime",
                "No liquidity sweep detected",
                "No FVG present",
                "Extreme volatility (>90th percentile)"
            ],
            "required_confirmations": 4
        }
    },
    {
        "strategy_id": "ICT_SILVER_BULLET",
        "name": "ICT Silver Bullet",
        "description": "Time-based ICT setup during London/NY kill zones. Requires FVG formation within specific hourly windows with structural alignment.",
        "evidence_grade": "A",
        "lifecycle_status": "ACTIVE",
        "rules": {
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH", "RANGING"],
            "sessions": ["LONDON", "NEW_YORK"],
            "preferred_timeframes": ["5m", "15m"],
            "volatility_filters": {"min_atr_percentile": 15.0, "max_atr_percentile": 80.0},
            "min_acceptable_rr": 2.0,
            "structure_requirements": {
                "bos_or_choch": False,
                "structure_bias_match": True
            },
            "liquidity_requirements": {
                "sweep_required": False,
                "fvg_required": True,
                "fvg_direction": "aligned"
            },
            "entry_conditions": [
                "Price within kill zone window (London 2-5 AM EST / NY 9-11 AM EST)",
                "Unmitigated FVG formed in kill zone",
                "Structure bias alignment"
            ],
            "invalidation_conditions": [
                "FVG fully mitigated before entry",
                "Price moves beyond kill zone range"
            ],
            "contraindications": [
                "Outside kill zone hours",
                "No FVG in kill zone",
                "High impact news within 30 min"
            ],
            "required_confirmations": 3
        }
    },
    {
        "strategy_id": "LONDON_BREAKOUT",
        "name": "London Breakout",
        "description": "Captures the initial London session expansion from Asian range consolidation. Requires clear range boundary break with momentum.",
        "evidence_grade": "B",
        "lifecycle_status": "ACTIVE",
        "rules": {
            "market_regimes": ["RANGING", "TRENDING_BULLISH", "TRENDING_BEARISH"],
            "sessions": ["LONDON"],
            "preferred_timeframes": ["15m", "1h"],
            "volatility_filters": {"min_atr_percentile": 25.0, "max_atr_percentile": 75.0},
            "min_acceptable_rr": 1.5,
            "structure_requirements": {
                "bos_or_choch": False,
                "structure_bias_match": False
            },
            "liquidity_requirements": {
                "sweep_required": False,
                "fvg_required": False
            },
            "entry_conditions": [
                "Asian session range clearly defined",
                "London candle breaks range high or low",
                "Momentum confirmation (ADX > 20)"
            ],
            "invalidation_conditions": [
                "Fakeout — price returns inside range within 2 candles",
                "No follow-through momentum"
            ],
            "contraindications": [
                "Already in strong trend (breakout less reliable)",
                "Asian range too tight (< 15 pips)",
                "High impact news at London open"
            ],
            "required_confirmations": 2
        }
    },
    {
        "strategy_id": "MEAN_REVERSION",
        "name": "Mean Reversion",
        "description": "Fades extreme moves in ranging/choppy markets. Enters at range extremes with RSI divergence and no structural breakout.",
        "evidence_grade": "B",
        "lifecycle_status": "ACTIVE",
        "rules": {
            "market_regimes": ["RANGING"],
            "sessions": ["LONDON", "NEW_YORK", "TOKYO"],
            "preferred_timeframes": ["15m", "1h"],
            "volatility_filters": {"min_atr_percentile": 10.0, "max_atr_percentile": 60.0},
            "min_acceptable_rr": 1.5,
            "structure_requirements": {
                "bos_or_choch": False,
                "structure_bias_match": False
            },
            "liquidity_requirements": {
                "sweep_required": False,
                "fvg_required": False
            },
            "entry_conditions": [
                "RANGING regime confirmed (ADX < 20)",
                "RSI at extreme (>70 or <30)",
                "Price at swing high/low boundary",
                "No BOS or CHoCH detected"
            ],
            "invalidation_conditions": [
                "BOS or CHoCH occurs (regime shift)",
                "ADX rises above 25"
            ],
            "contraindications": [
                "TRENDING regime",
                "Strong directional structure",
                "BOS/CHoCH present",
                "High volatility expansion"
            ],
            "required_confirmations": 3
        }
    },
    {
        "strategy_id": "TREND_CONTINUATION",
        "name": "Trend Continuation (BOS Pullback)",
        "description": "Enters on pullback into FVG/order block after confirmed Break of Structure in trending market.",
        "evidence_grade": "A",
        "lifecycle_status": "ACTIVE",
        "rules": {
            "market_regimes": ["TRENDING_BULLISH", "TRENDING_BEARISH"],
            "sessions": ["LONDON", "NEW_YORK"],
            "preferred_timeframes": ["15m", "1h", "4h"],
            "volatility_filters": {"min_atr_percentile": 20.0, "max_atr_percentile": 80.0},
            "min_acceptable_rr": 2.0,
            "structure_requirements": {
                "bos_or_choch": True,
                "structure_bias_match": True
            },
            "liquidity_requirements": {
                "sweep_required": False,
                "fvg_required": True,
                "fvg_direction": "aligned"
            },
            "entry_conditions": [
                "BOS confirmed in trend direction",
                "Pullback into unmitigated FVG",
                "Structure bias alignment",
                "Trending regime (ADX > 25)"
            ],
            "invalidation_conditions": [
                "CHoCH against trend",
                "FVG fully mitigated without reaction"
            ],
            "contraindications": [
                "RANGING regime",
                "No BOS detected",
                "No FVG for pullback entry",
                "CHoCH against trend direction"
            ],
            "required_confirmations": 3
        }
    }
]

def get_builtin_strategies() -> List[Dict[str, Any]]:
    return BUILTIN_STRATEGIES

def get_strategy_by_id(strategy_id: str) -> Dict[str, Any]:
    for s in BUILTIN_STRATEGIES:
        if s["strategy_id"] == strategy_id:
            return s
    return {}
