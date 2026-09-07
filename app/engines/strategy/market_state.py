"""
Market State Analyzer - Module 1 of Strategy Engine.
Determines current regime, trend, volatility, momentum, structure.
All DETERMINISTIC - no AI guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.engines.indicators.technical import TechnicalSnapshot


@dataclass
class MarketState:
    instrument: str
    captured_at: datetime

    # Regime
    regime: str  # TRENDING_BULLISH | TRENDING_BEARISH | RANGING | BREAKOUT_PENDING | HIGH_VOLATILITY_UNCLEAR

    # From TechnicalSnapshot
    trend_strength: float  # ADX value
    trend_direction: str
    volatility_state: str
    volatility_pct: float  # ATR as percentile (approximated from atr_pct)
    momentum_direction: str
    rsi: float
    macd_histogram: float

    # Structure
    nearest_support: float | None = None
    nearest_resistance: float | None = None
    structure_confirmed: bool = False
    structure_bias: str = "unclear"

    # Session
    session: str = "UNKNOWN"

    # Spread/Liquidity (placeholder until live spread feed)
    spread_state: str = "NORMAL"
    liquidity_state: str = "NORMAL"

    # News (placeholder until news feed integrated)
    news_risk: str = "none"


def classify_regime(adx: float, trend_direction: str, atr_pct: float) -> str:
    """Rule-based regime classification. Auditable, deterministic."""
    # Extreme volatility overrides everything
    if atr_pct > 1.5:
        return "HIGH_VOLATILITY_UNCLEAR"

    # Strong trend
    if adx >= 25:
        if trend_direction == "bullish":
            return "TRENDING_BULLISH"
        elif trend_direction == "bearish":
            return "TRENDING_BEARISH"

    # Weak trend / no trend
    if adx < 20:
        return "RANGING"

    # ADX between 20-25: could be building
    return "BREAKOUT_PENDING"


def get_current_session() -> str:
    """Determine trading session from UTC time."""
    now = datetime.now(timezone.utc)
    hour = now.hour

    # Session windows (approximate UTC)
    if 22 <= hour or hour < 6:
        # Check overlap
        if 0 <= hour < 6:
            return "TOKYO"
        return "SYDNEY"
    elif 6 <= hour < 8:
        return "TOKYO"
    elif 8 <= hour < 12:
        return "LONDON"
    elif 12 <= hour < 17:
        return "LONDON_NY_OVERLAP"
    elif 17 <= hour < 22:
        return "NEW_YORK"
    return "UNKNOWN"


def build_market_state(instrument: str, snap: TechnicalSnapshot) -> MarketState:
    """Build a complete MarketState from a TechnicalSnapshot."""
    regime = classify_regime(snap.trend_strength, snap.trend_direction, snap.atr_pct)
    session = get_current_session()

    # Approximate volatility percentile from atr_pct
    # Low < 0.30, Normal 0.30-0.80, High 0.80-1.50, Extreme > 1.50
    if snap.atr_pct < 0.30:
        vol_pct = 15.0
    elif snap.atr_pct < 0.50:
        vol_pct = 40.0
    elif snap.atr_pct < 0.80:
        vol_pct = 60.0
    elif snap.atr_pct < 1.20:
        vol_pct = 80.0
    elif snap.atr_pct < 1.50:
        vol_pct = 92.0
    else:
        vol_pct = 98.0

    return MarketState(
        instrument=instrument,
        captured_at=datetime.now(timezone.utc),
        regime=regime,
        trend_strength=snap.trend_strength,
        trend_direction=snap.trend_direction,
        volatility_state=snap.volatility_state,
        volatility_pct=vol_pct,
        momentum_direction=snap.momentum_direction,
        rsi=snap.rsi,
        macd_histogram=snap.macd_histogram,
        nearest_support=snap.nearest_support,
        nearest_resistance=snap.nearest_resistance,
        structure_confirmed=snap.structure_confirmed,
        structure_bias=snap.structure_bias,
        session=session,
    )
