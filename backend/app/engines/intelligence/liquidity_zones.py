"""
Liquidity Zone Ranking Engine (Phase 2B)
=========================================
Deterministic Order Block & Fair Value Gap detection with
institutional-zone-candidate scoring.

NAMING: "institutional-zone candidate" / "high-quality liquidity zone"
We do NOT claim actual institutional order presence (requires order-book data).

Scoring: 0-100 based on Volume Imbalance, Displacement, Freshness, Age Decay.
Insufficient data → UNAVAILABLE (Golden Rule #3: NO_TRADE > Bad Trade).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from app.engines.intelligence.liquidity_sweep import CandleData


# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

class ZoneType(str, Enum):
    BULLISH_OB = "BULLISH_OB"
    BEARISH_OB = "BEARISH_OB"
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"


@dataclass
class LiquidityZone:
    """A detected institutional-zone candidate."""
    zone_type: ZoneType
    price_high: float
    price_low: float
    creation_bar: int
    score: float = 0.0

    # Component scores (0.0 to 1.0 each)
    volume_imbalance: float = 0.0
    displacement_strength: float = 0.0
    freshness: float = 1.0
    age_decay: float = 1.0

    # Tracking
    touch_count: int = 0
    is_mitigated: bool = False
    bars_since_creation: int = 0

    @property
    def midpoint(self) -> float:
        return (self.price_high + self.price_low) / 2.0

    @property
    def width_pips(self) -> float:
        return abs(self.price_high - self.price_low) / 0.0001


@dataclass
class ZoneRankingResult:
    """Complete zone ranking output."""
    symbol: str
    timeframe: str
    status: str = "ACTIVE"  # "ACTIVE" or "UNAVAILABLE"
    reason: str = ""
    total_zones_detected: int = 0
    top_zones: List[LiquidityZone] = field(default_factory=list)
    analysis_timestamp: float = 0.0


# ─────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────

class LiquidityZoneRankingEngine:
    """
    Deterministic Liquidity Zone Detection & Ranking Engine.

    Usage:
        engine = LiquidityZoneRankingEngine()
        result = engine.analyze(candles, symbol="EURUSD", timeframe="H1")
    """

    def __init__(
        self,
        min_candles: int = 50,
        atr_period: int = 14,
        volume_ma_period: int = 20,
        displacement_atr_mult: float = 1.5,
        min_score_threshold: float = 25.0,
        top_n: int = 3,
        age_decay_bars: int = 200,
        pip_size: float = 0.0001,
    ):
        self.min_candles = min_candles
        self.atr_period = atr_period
        self.volume_ma_period = volume_ma_period
        self.displacement_atr_mult = displacement_atr_mult
        self.min_score_threshold = min_score_threshold
        self.top_n = top_n
        self.age_decay_bars = age_decay_bars
        self.pip_size = pip_size

    # ── ATR Calculation ──────────────────────────────────────

    def _calculate_atr(self, candles: List[CandleData]) -> float:
        if len(candles) < self.atr_period + 1:
            return 0.0
        tr_values = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i - 1].close),
                abs(candles[i].low - candles[i - 1].close),
            )
            tr_values.append(tr)
        if not tr_values:
            return 0.0
        recent = tr_values[-self.atr_period:]
        return sum(recent) / len(recent)

    # ── Volume MA ────────────────────────────────────────────

    def _volume_ma(self, candles: List[CandleData]) -> float:
        if not candles:
            return 0.0
        recent = candles[-self.volume_ma_period:]
        return sum(c.volume for c in recent) / len(recent)

    # ── FVG Detection ────────────────────────────────────────

    def _detect_fvgs(self, candles: List[CandleData]) -> List[LiquidityZone]:
        """
        Detect Fair Value Gaps (3-candle imbalance).
        Bullish FVG: candle[i-2].high < candle[i].low
        Bearish FVG: candle[i-2].low > candle[i].high
        """
        zones: List[LiquidityZone] = []
        for i in range(2, len(candles)):
            # Bullish FVG
            if candles[i - 2].high < candles[i].low:
                zones.append(LiquidityZone(
                    zone_type=ZoneType.BULLISH_FVG,
                    price_high=candles[i].low,
                    price_low=candles[i - 2].high,
                    creation_bar=i - 1,
                ))
            # Bearish FVG
            elif candles[i - 2].low > candles[i].high:
                zones.append(LiquidityZone(
                    zone_type=ZoneType.BEARISH_FVG,
                    price_high=candles[i - 2].low,
                    price_low=candles[i].high,
                    creation_bar=i - 1,
                ))
        return zones

    # ── Order Block Detection ────────────────────────────────

    def _detect_order_blocks(self, candles: List[CandleData], atr: float) -> List[LiquidityZone]:
        """
        Detect Order Blocks: last opposing candle before displacement move.
        Bullish OB: last bearish candle before ≥2 bullish displacement candles.
        Bearish OB: last bullish candle before ≥2 bearish displacement candles.
        """
        if atr <= 0:
            return []

        zones: List[LiquidityZone] = []
        displacement_threshold = self.displacement_atr_mult * atr

        for i in range(1, len(candles) - 2):
            # Check if candles[i+1] and candles[i+2] are displacement candles
            c1 = candles[i + 1]
            c2 = candles[i + 2]

            c1_body = c1.close - c1.open
            c2_body = c2.close - c2.open

            # Bullish OB: candle[i] is bearish, followed by 2 bullish displacement
            if (candles[i].close < candles[i].open and
                    c1_body > displacement_threshold and
                    c2_body > displacement_threshold):
                zones.append(LiquidityZone(
                    zone_type=ZoneType.BULLISH_OB,
                    price_high=candles[i].high,
                    price_low=candles[i].low,
                    creation_bar=i,
                ))

            # Bearish OB: candle[i] is bullish, followed by 2 bearish displacement
            elif (candles[i].close > candles[i].open and
                  c1_body < -displacement_threshold and
                  c2_body < -displacement_threshold):
                zones.append(LiquidityZone(
                    zone_type=ZoneType.BEARISH_OB,
                    price_high=candles[i].high,
                    price_low=candles[i].low,
                    creation_bar=i,
                ))

        return zones

    # ── Zone Scoring ─────────────────────────────────────────

    def _score_zone(
        self,
        zone: LiquidityZone,
        candles: List[CandleData],
        atr: float,
        vol_ma: float,
    ) -> LiquidityZone:
        """Score a single zone using the 4-factor formula."""
        total_bars = len(candles)
        zone.bars_since_creation = total_bars - 1 - zone.creation_bar

        # 1. Volume Imbalance (0.0 to 1.0)
        if zone.creation_bar < len(candles):
            zone_vol = candles[zone.creation_bar].volume
            if vol_ma > 0:
                zone.volume_imbalance = min(zone_vol / vol_ma, 3.0) / 3.0
            else:
                zone.volume_imbalance = 0.5  # Neutral when no volume data
        else:
            zone.volume_imbalance = 0.5

        # 2. Displacement Strength (0.0 to 1.0)
        if atr > 0:
            zone_width = abs(zone.price_high - zone.price_low)
            zone.displacement_strength = min(zone_width / (2.0 * atr), 1.0)
        else:
            zone.displacement_strength = 0.0

        # 3. Freshness (1.0 = unmitigated, decays with touches)
        # Check how many times price re-entered the zone after creation
        touches = 0
        for j in range(zone.creation_bar + 1, total_bars):
            c = candles[j]
            # Price overlaps with zone
            if c.low <= zone.price_high and c.high >= zone.price_low:
                touches += 1
        zone.touch_count = touches
        zone.freshness = round(max(0.0, 1.0 - (touches * 0.3)), 2)
        zone.is_mitigated = touches >= 3

        # 4. Age Decay (0.1 to 1.0)
        zone.age_decay = max(0.1, 1.0 - (zone.bars_since_creation / self.age_decay_bars))

        # Final Score (0-100)
        zone.score = round(
            (
                zone.volume_imbalance * 0.35
                + zone.displacement_strength * 0.25
                + zone.freshness * 0.25
                + zone.age_decay * 0.15
            ) * 100,
            2,
        )

        return zone

    # ── Main Analysis ────────────────────────────────────────

    def analyze(
        self,
        candles: List[CandleData],
        symbol: str = "EURUSD",
        timeframe: str = "H1",
    ) -> ZoneRankingResult:
        """
        Full zone detection, scoring, and ranking pipeline.
        Returns UNAVAILABLE if insufficient data (Golden Rule #3).
        """
        import time as _time

        # Guard: insufficient data
        if len(candles) < self.min_candles:
            return ZoneRankingResult(
                symbol=symbol,
                timeframe=timeframe,
                status="UNAVAILABLE",
                reason=f"Insufficient data: {len(candles)} candles < {self.min_candles} minimum",
                analysis_timestamp=_time.time(),
            )

        atr = self._calculate_atr(candles)
        if atr <= 0:
            return ZoneRankingResult(
                symbol=symbol,
                timeframe=timeframe,
                status="UNAVAILABLE",
                reason="ATR is zero — cannot compute displacement thresholds",
                analysis_timestamp=_time.time(),
            )

        vol_ma = self._volume_ma(candles)

        # Detect all zones
        fvg_zones = self._detect_fvgs(candles)
        ob_zones = self._detect_order_blocks(candles, atr)
        all_zones = fvg_zones + ob_zones

        if not all_zones:
            return ZoneRankingResult(
                symbol=symbol,
                timeframe=timeframe,
                status="ACTIVE",
                reason="No institutional-zone candidates detected in current window",
                total_zones_detected=0,
                top_zones=[],
                analysis_timestamp=_time.time(),
            )

        # Score all zones
        scored_zones = [
            self._score_zone(z, candles, atr, vol_ma) for z in all_zones
        ]

        # Filter by minimum threshold
        qualified = [z for z in scored_zones if z.score >= self.min_score_threshold]

        # Sort: score DESC → touch_count ASC → bars_since_creation ASC
        qualified.sort(
            key=lambda z: (-z.score, z.touch_count, z.bars_since_creation)
        )

        # Top N
        top_zones = qualified[: self.top_n]

        return ZoneRankingResult(
            symbol=symbol,
            timeframe=timeframe,
            status="ACTIVE",
            total_zones_detected=len(all_zones),
            top_zones=top_zones,
            analysis_timestamp=_time.time(),
        )
