"""
Liquidity Sweep Statistics Engine (Phase 2A)
=============================================
Institutional-grade stop-hunt / liquidity raid detection engine.

Detects Equal Highs/Lows (EQH/EQL), swing point liquidity pools,
and quantifies sweep events using pure mathematical evidence.

NO AI. NO subjective interpretation. Pure deterministic math.
Evidence weight capped at 15% per Golden Rule #8.

Core Metrics:
- Sweep Depth (pips & ATR multiples)
- Wick Rejection Ratio (0.0 to 1.0)
- Volume Spike Ratio (vs 20-period MA)
- Confidence Score (0.0 to 1.0)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

@dataclass
class CandleData:
    """Single OHLCV candle. All prices in quote currency (e.g., 1.0850)."""
    timestamp: float
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0
    spread_pips: float = 0.0


@dataclass
class SwingPoint:
    """A detected swing high or swing low."""
    price: float
    bar_index: int
    swing_type: str  # "HIGH" or "LOW"
    strength: int = 1  # How many times tested


class LiquidityLevelType(str, Enum):
    EQUAL_HIGHS = "EQH"
    EQUAL_LOWS = "EQL"
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    PREVIOUS_DAY_HIGH = "PDH"
    PREVIOUS_DAY_LOW = "PDL"


@dataclass
class LiquidityLevel:
    """A clustered liquidity zone (EQH/EQL or swing pool)."""
    price: float
    level_type: LiquidityLevelType
    touch_count: int = 1
    tolerance_pips: float = 2.0
    bars_ago: int = 0
    swept: bool = False


class SweepDirection(str, Enum):
    BUY_SIDE = "BUY_SIDE"   # Swept above resistance (stop hunt on shorts)
    SELL_SIDE = "SELL_SIDE"  # Swept below support (stop hunt on longs)


@dataclass
class SweepEvent:
    """A confirmed liquidity sweep / stop-hunt event."""
    timestamp: float
    direction: SweepDirection
    liquidity_level_price: float
    level_type: LiquidityLevelType

    # Core Metrics
    sweep_depth_pips: float = 0.0
    sweep_depth_atr: float = 0.0
    wick_rejection_ratio: float = 0.0
    volume_spike_ratio: float = 0.0
    candle_body_ratio: float = 0.0

    # Evidence
    confidence_score: float = 0.0
    is_confirmed: bool = False

    # Metadata
    symbol: str = ""
    timeframe: str = ""
    bars_since_sweep: int = 0


@dataclass
class SweepAnalysisResult:
    """Complete sweep analysis output for a symbol/timeframe."""
    symbol: str
    timeframe: str
    total_swing_highs: int = 0
    total_swing_lows: int = 0
    liquidity_levels: List[LiquidityLevel] = field(default_factory=list)
    recent_sweeps: List[SweepEvent] = field(default_factory=list)
    active_sweep: Optional[SweepEvent] = None
    sweep_bias: str = "NEUTRAL"  # "FADE_BUY", "FADE_SELL", "NEUTRAL"
    evidence_weight: float = 0.0  # Capped at 0.15 (15%)
    analysis_timestamp: float = 0.0


# ─────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────

class LiquiditySweepEngine:
    """
    Deterministic Liquidity Sweep Detection Engine.

    Usage:
        engine = LiquiditySweepEngine(swing_lookback=5, eqh_tolerance_pips=2.0)
        result = engine.analyze(candles, symbol="EURUSD", timeframe="H1")
    """

    def __init__(
        self,
        swing_lookback: int = 5,
        eqh_tolerance_pips: float = 2.0,
        volume_ma_period: int = 20,
        min_sweep_depth_pips: float = 1.0,
        max_evidence_weight: float = 0.15,
        pip_size: float = 0.0001,
    ):
        self.swing_lookback = swing_lookback
        self.eqh_tolerance_pips = eqh_tolerance_pips
        self.volume_ma_period = volume_ma_period
        self.min_sweep_depth_pips = min_sweep_depth_pips
        self.max_evidence_weight = max_evidence_weight
        self.pip_size = pip_size

    # ── Swing Detection ──────────────────────────────────────

    def detect_swing_points(self, candles: List[CandleData]) -> List[SwingPoint]:
        """
        Detect swing highs and swing lows using N-bar lookback.
        A swing high at bar[i] means high[i] >= high[i-k] for k in 1..N on both sides.
        """
        if len(candles) < 2 * self.swing_lookback + 1:
            return []

        swings: List[SwingPoint] = []
        n = self.swing_lookback

        for i in range(n, len(candles) - n):
            # Swing High
            is_swing_high = True
            for k in range(1, n + 1):
                if candles[i].high < candles[i - k].high or candles[i].high < candles[i + k].high:
                    is_swing_high = False
                    break
            if is_swing_high:
                swings.append(SwingPoint(
                    price=candles[i].high,
                    bar_index=i,
                    swing_type="HIGH",
                ))

            # Swing Low
            is_swing_low = True
            for k in range(1, n + 1):
                if candles[i].low > candles[i - k].low or candles[i].low > candles[i + k].low:
                    is_swing_low = False
                    break
            if is_swing_low:
                swings.append(SwingPoint(
                    price=candles[i].low,
                    bar_index=i,
                    swing_type="LOW",
                ))

        return swings

    # ── Liquidity Level Clustering ───────────────────────────

    def find_liquidity_levels(
        self, swings: List[SwingPoint], total_bars: int
    ) -> List[LiquidityLevel]:
        """
        Cluster swing points into EQH/EQL liquidity zones.
        Two swings within eqh_tolerance_pips are considered "equal".
        """
        if not swings:
            return []

        tolerance = self.eqh_tolerance_pips * self.pip_size
        levels: List[LiquidityLevel] = []
        used = set()

        highs = sorted([s for s in swings if s.swing_type == "HIGH"], key=lambda s: s.price)
        lows = sorted([s for s in swings if s.swing_type == "LOW"], key=lambda s: s.price)

        # Cluster Equal Highs
        for i, sh in enumerate(highs):
            if id(sh) in used:
                continue
            cluster = [sh]
            used.add(id(sh))
            for j in range(i + 1, len(highs)):
                if id(highs[j]) in used:
                    continue
                if abs(highs[j].price - sh.price) <= tolerance:
                    cluster.append(highs[j])
                    used.add(id(highs[j]))

            avg_price = sum(s.price for s in cluster) / len(cluster)
            level_type = LiquidityLevelType.EQUAL_HIGHS if len(cluster) >= 2 else LiquidityLevelType.SWING_HIGH
            bars_ago = total_bars - 1 - max(s.bar_index for s in cluster)
            levels.append(LiquidityLevel(
                price=avg_price,
                level_type=level_type,
                touch_count=len(cluster),
                tolerance_pips=self.eqh_tolerance_pips,
                bars_ago=bars_ago,
            ))

        # Cluster Equal Lows
        for i, sl in enumerate(lows):
            if id(sl) in used:
                continue
            cluster = [sl]
            used.add(id(sl))
            for j in range(i + 1, len(lows)):
                if id(lows[j]) in used:
                    continue
                if abs(lows[j].price - sl.price) <= tolerance:
                    cluster.append(lows[j])
                    used.add(id(lows[j]))

            avg_price = sum(s.price for s in cluster) / len(cluster)
            level_type = LiquidityLevelType.EQUAL_LOWS if len(cluster) >= 2 else LiquidityLevelType.SWING_LOW
            bars_ago = total_bars - 1 - max(s.bar_index for s in cluster)
            levels.append(LiquidityLevel(
                price=avg_price,
                level_type=level_type,
                touch_count=len(cluster),
                tolerance_pips=self.eqh_tolerance_pips,
                bars_ago=bars_ago,
            ))

        return sorted(levels, key=lambda lv: lv.touch_count, reverse=True)

    # ── ATR Calculation ──────────────────────────────────────

    def _calculate_atr(self, candles: List[CandleData], period: int = 14) -> float:
        """Average True Range over the last `period` candles."""
        if len(candles) < period + 1:
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

        recent = tr_values[-period:]
        return sum(recent) / len(recent)

    # ── Volume Moving Average ────────────────────────────────

    def _volume_ma(self, candles: List[CandleData], period: int = 20) -> float:
        """Simple moving average of volume."""
        if not candles:
            return 0.0
        recent = candles[-period:]
        return sum(c.volume for c in recent) / len(recent)

    # ── Sweep Detection ──────────────────────────────────────

    def detect_sweeps(
        self,
        candles: List[CandleData],
        levels: List[LiquidityLevel],
    ) -> List[SweepEvent]:
        """
        Detect liquidity sweeps: candle wick penetrates a liquidity level
        but the candle body closes back inside (rejection).
        """
        if len(candles) < 2 or not levels:
            return []

        atr = self._calculate_atr(candles)
        vol_ma = self._volume_ma(candles, self.volume_ma_period)
        sweeps: List[SweepEvent] = []

        # Check last 10 candles for sweeps
        lookback = min(10, len(candles))
        for i in range(len(candles) - lookback, len(candles)):
            candle = candles[i]
            candle_range = candle.high - candle.low
            if candle_range <= 0:
                continue

            body_top = max(candle.open, candle.close)
            body_bottom = min(candle.open, candle.close)
            body_size = body_top - body_bottom

            for level in levels:
                if level.swept:
                    continue

                tolerance = level.tolerance_pips * self.pip_size

                # BUY-SIDE SWEEP: Wick above resistance, close below
                if (
                    level.level_type in (LiquidityLevelType.EQUAL_HIGHS, LiquidityLevelType.SWING_HIGH)
                    and candle.high > level.price
                    and body_top < level.price + tolerance
                    and candle.close < level.price
                ):
                    depth_pips = (candle.high - level.price) / self.pip_size
                    if depth_pips < self.min_sweep_depth_pips:
                        continue

                    upper_wick = candle.high - body_top
                    wick_ratio = upper_wick / candle_range if candle_range > 0 else 0.0
                    vol_ratio = candle.volume / vol_ma if vol_ma > 0 else 1.0
                    depth_atr = (candle.high - level.price) / atr if atr > 0 else 0.0
                    body_ratio = body_size / candle_range if candle_range > 0 else 0.0

                    confidence = self._compute_confidence(
                        wick_ratio=wick_ratio,
                        depth_atr=depth_atr,
                        vol_ratio=vol_ratio,
                        touch_count=level.touch_count,
                    )

                    sweeps.append(SweepEvent(
                        timestamp=candle.timestamp,
                        direction=SweepDirection.BUY_SIDE,
                        liquidity_level_price=level.price,
                        level_type=level.level_type,
                        sweep_depth_pips=round(depth_pips, 2),
                        sweep_depth_atr=round(depth_atr, 3),
                        wick_rejection_ratio=round(wick_ratio, 3),
                        volume_spike_ratio=round(vol_ratio, 2),
                        candle_body_ratio=round(body_ratio, 3),
                        confidence_score=round(confidence, 3),
                        is_confirmed=confidence >= 0.6,
                        bars_since_sweep=len(candles) - 1 - i,
                    ))
                    level.swept = True

                # SELL-SIDE SWEEP: Wick below support, close above
                elif (
                    level.level_type in (LiquidityLevelType.EQUAL_LOWS, LiquidityLevelType.SWING_LOW)
                    and candle.low < level.price
                    and body_bottom > level.price - tolerance
                    and candle.close > level.price
                ):
                    depth_pips = (level.price - candle.low) / self.pip_size
                    if depth_pips < self.min_sweep_depth_pips:
                        continue

                    lower_wick = body_bottom - candle.low
                    wick_ratio = lower_wick / candle_range if candle_range > 0 else 0.0
                    vol_ratio = candle.volume / vol_ma if vol_ma > 0 else 1.0
                    depth_atr = (level.price - candle.low) / atr if atr > 0 else 0.0
                    body_ratio = body_size / candle_range if candle_range > 0 else 0.0

                    confidence = self._compute_confidence(
                        wick_ratio=wick_ratio,
                        depth_atr=depth_atr,
                        vol_ratio=vol_ratio,
                        touch_count=level.touch_count,
                    )

                    sweeps.append(SweepEvent(
                        timestamp=candle.timestamp,
                        direction=SweepDirection.SELL_SIDE,
                        liquidity_level_price=level.price,
                        level_type=level.level_type,
                        sweep_depth_pips=round(depth_pips, 2),
                        sweep_depth_atr=round(depth_atr, 3),
                        wick_rejection_ratio=round(wick_ratio, 3),
                        volume_spike_ratio=round(vol_ratio, 2),
                        candle_body_ratio=round(body_ratio, 3),
                        confidence_score=round(confidence, 3),
                        is_confirmed=confidence >= 0.6,
                        bars_since_sweep=len(candles) - 1 - i,
                    ))
                    level.swept = True

        return sweeps

    # ── Confidence Computation (Pure Math) ───────────────────

    def _compute_confidence(
        self,
        wick_ratio: float,
        depth_atr: float,
        vol_ratio: float,
        touch_count: int,
    ) -> float:
        """
        Compute sweep confidence score (0.0 to 1.0) from 4 weighted factors.

        Weights:
        - Wick Rejection Ratio: 35% (higher = stronger rejection)
        - Volume Spike:         25% (higher = more institutional activity)
        - Touch Count:          20% (more touches = stronger level)
        - Sweep Depth (ATR):    20% (moderate depth = ideal, too deep = breakout)
        """
        # Wick score: 0.5-1.0 range is ideal (strong rejection)
        wick_score = min(wick_ratio / 0.7, 1.0) if wick_ratio > 0 else 0.0

        # Volume score: 1.5x-3.0x is ideal
        vol_score = min(max(vol_ratio - 1.0, 0.0) / 2.0, 1.0)

        # Touch count score: 2-5 touches is ideal
        touch_score = min(touch_count / 4.0, 1.0)

        # Depth score: 0.5-1.5 ATR is ideal; >2.0 ATR suggests real breakout (lower confidence)
        if depth_atr <= 0:
            depth_score = 0.0
        elif depth_atr <= 1.5:
            depth_score = min(depth_atr / 1.0, 1.0)
        else:
            depth_score = max(1.0 - (depth_atr - 1.5) * 0.5, 0.1)

        confidence = (
            wick_score * 0.35
            + vol_score * 0.25
            + touch_score * 0.20
            + depth_score * 0.20
        )

        return max(0.0, min(confidence, 1.0))

    # ── Main Analysis Entry Point ────────────────────────────

    def analyze(
        self,
        candles: List[CandleData],
        symbol: str = "EURUSD",
        timeframe: str = "H1",
    ) -> SweepAnalysisResult:
        """
        Full sweep analysis pipeline:
        1. Detect swing points
        2. Cluster into liquidity levels (EQH/EQL)
        3. Detect sweeps on recent candles
        4. Compute confidence & evidence weight
        """
        import time as _time

        if len(candles) < 2 * self.swing_lookback + 2:
            return SweepAnalysisResult(
                symbol=symbol,
                timeframe=timeframe,
                analysis_timestamp=_time.time(),
            )

        swings = self.detect_swing_points(candles)
        swing_highs = [s for s in swings if s.swing_type == "HIGH"]
        swing_lows = [s for s in swings if s.swing_type == "LOW"]

        levels = self.find_liquidity_levels(swings, len(candles))
        sweeps = self.detect_sweeps(candles, levels)

        # Determine sweep bias
        sweep_bias = "NEUTRAL"
        active_sweep: Optional[SweepEvent] = None
        if sweeps:
            confirmed = [s for s in sweeps if s.is_confirmed]
            if confirmed:
                latest = max(confirmed, key=lambda s: s.timestamp)
                active_sweep = latest
                if latest.direction == SweepDirection.BUY_SIDE:
                    sweep_bias = "FADE_SELL"  # Swept highs → expect reversal down
                else:
                    sweep_bias = "FADE_BUY"   # Swept lows → expect reversal up

        # Evidence weight: confidence * max_weight, capped at 15%
        evidence_weight = 0.0
        if active_sweep:
            evidence_weight = min(
                active_sweep.confidence_score * self.max_evidence_weight / 0.8,
                self.max_evidence_weight,
            )

        return SweepAnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            total_swing_highs=len(swing_highs),
            total_swing_lows=len(swing_lows),
            liquidity_levels=levels,
            recent_sweeps=sweeps,
            active_sweep=active_sweep,
            sweep_bias=sweep_bias,
            evidence_weight=round(evidence_weight, 4),
            analysis_timestamp=_time.time(),
        )
