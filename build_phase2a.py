import os
import sys
import time
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"

def log(msg, color="\033[96m"):
    print(f"{color}===> {msg}\033[0m", flush=True)

def error_exit(msg):
    print(f"\n\033[91m❌ ERROR: {msg}\033[0m\n", flush=True)
    sys.exit(1)

def run_cmd(cmd, cwd, desc=""):
    if desc:
        log(desc)
    print(f"[CMD] {cmd}", flush=True)
    res = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if res.returncode != 0:
        error_exit(f"Command failed with code {res.returncode}: {cmd}")
    return res

def kill_ports(ports):
    for port in ports:
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"'
            out = subprocess.check_output(cmd, shell=True, text=True).strip()
            if out:
                for pid in [p.strip() for p in out.splitlines() if p.strip().isdigit() and p.strip() != "0"]:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(1)

# ═══════════════════════════════════════════════════════════════
# STEP 1: Create Liquidity Sweep Engine Module
# ═══════════════════════════════════════════════════════════════
log("STEP 1: Building Liquidity Sweep Statistics Engine...", "\033[93m")

intel_dir = BACKEND / "app" / "engines" / "intelligence"
intel_dir.mkdir(parents=True, exist_ok=True)

# Ensure __init__.py exists
init_file = intel_dir / "__init__.py"
if not init_file.exists():
    init_file.write_text("# Market Intelligence Engines\n", encoding="utf-8")

sweep_engine_path = intel_dir / "liquidity_sweep.py"
sweep_engine_code = '''"""
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
'''

sweep_engine_path.write_text(sweep_engine_code, encoding="utf-8")
log("✅ liquidity_sweep.py engine created", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 2: Create Comprehensive Test Suite
# ═══════════════════════════════════════════════════════════════
log("STEP 2: Building test suite for Liquidity Sweep Engine...", "\033[93m")

test_path = BACKEND / "tests" / "test_liquidity_sweep_engine.py"
test_code = '''"""
Tests for Phase 2A: Liquidity Sweep Statistics Engine.
Deterministic, no AI, pure mathematical verification.
"""
import pytest
import time
from app.engines.intelligence.liquidity_sweep import (
    CandleData,
    SwingPoint,
    LiquidityLevel,
    LiquidityLevelType,
    SweepEvent,
    SweepDirection,
    SweepAnalysisResult,
    LiquiditySweepEngine,
)


def _make_candle(ts, o, h, l, c, vol=1000.0):
    return CandleData(timestamp=ts, open=o, high=h, low=l, close=c, volume=vol)


def _make_flat_candles(n=50, base=1.0850, pip=0.0001):
    """Generate flat range-bound candles for baseline."""
    candles = []
    for i in range(n):
        candles.append(_make_candle(
            ts=float(i),
            o=base,
            h=base + 5 * pip,
            l=base - 5 * pip,
            c=base,
            vol=1000.0,
        ))
    return candles


class TestSwingDetection:
    """Verify swing high/low detection with N-bar lookback."""

    def test_detects_swing_high_in_v_pattern(self):
        engine = LiquiditySweepEngine(swing_lookback=2)
        pip = 0.0001
        candles = [
            _make_candle(0, 1.080, 1.082, 1.079, 1.081),
            _make_candle(1, 1.081, 1.084, 1.080, 1.083),
            _make_candle(2, 1.083, 1.090, 1.082, 1.088),  # Swing High
            _make_candle(3, 1.088, 1.086, 1.081, 1.083),
            _make_candle(4, 1.083, 1.084, 1.080, 1.081),
        ]
        swings = engine.detect_swing_points(candles)
        highs = [s for s in swings if s.swing_type == "HIGH"]
        assert len(highs) >= 1
        assert any(abs(s.price - 1.090) < pip for s in highs)

    def test_detects_swing_low_in_a_pattern(self):
        engine = LiquiditySweepEngine(swing_lookback=2)
        pip = 0.0001
        candles = [
            _make_candle(0, 1.090, 1.091, 1.088, 1.089),
            _make_candle(1, 1.089, 1.090, 1.086, 1.087),
            _make_candle(2, 1.087, 1.088, 1.080, 1.082),  # Swing Low
            _make_candle(3, 1.082, 1.086, 1.083, 1.085),
            _make_candle(4, 1.085, 1.088, 1.084, 1.087),
        ]
        swings = engine.detect_swing_points(candles)
        lows = [s for s in swings if s.swing_type == "LOW"]
        assert len(lows) >= 1
        assert any(abs(s.price - 1.080) < pip for s in lows)

    def test_insufficient_data_returns_empty(self):
        engine = LiquiditySweepEngine(swing_lookback=5)
        candles = _make_flat_candles(5)
        swings = engine.detect_swing_points(candles)
        assert swings == []


class TestLiquidityLevelClustering:
    """Verify EQH/EQL clustering logic."""

    def test_equal_highs_clustered_within_tolerance(self):
        engine = LiquiditySweepEngine(eqh_tolerance_pips=2.0)
        pip = 0.0001
        swings = [
            SwingPoint(price=1.0900, bar_index=5, swing_type="HIGH"),
            SwingPoint(price=1.0901, bar_index=15, swing_type="HIGH"),  # Within 2 pips
            SwingPoint(price=1.0950, bar_index=25, swing_type="HIGH"),  # Far away
        ]
        levels = engine.find_liquidity_levels(swings, total_bars=30)
        eqh_levels = [lv for lv in levels if lv.level_type == LiquidityLevelType.EQUAL_HIGHS]
        assert len(eqh_levels) >= 1
        assert eqh_levels[0].touch_count == 2

    def test_single_swing_not_classified_as_eqh(self):
        engine = LiquiditySweepEngine(eqh_tolerance_pips=2.0)
        swings = [
            SwingPoint(price=1.0900, bar_index=5, swing_type="HIGH"),
        ]
        levels = engine.find_liquidity_levels(swings, total_bars=30)
        eqh = [lv for lv in levels if lv.level_type == LiquidityLevelType.EQUAL_HIGHS]
        assert len(eqh) == 0
        swing_h = [lv for lv in levels if lv.level_type == LiquidityLevelType.SWING_HIGH]
        assert len(swing_h) == 1


class TestSweepDetection:
    """Verify buy-side and sell-side sweep detection."""

    def test_buy_side_sweep_detected(self):
        """Wick above EQH, close below = buy-side sweep (stop hunt on shorts)."""
        engine = LiquiditySweepEngine(swing_lookback=2, min_sweep_depth_pips=1.0)
        pip = 0.0001
        level_price = 1.0900

        levels = [
            LiquidityLevel(
                price=level_price,
                level_type=LiquidityLevelType.EQUAL_HIGHS,
                touch_count=3,
                tolerance_pips=2.0,
            )
        ]

        candles = _make_flat_candles(20, base=1.0850)
        # Add sweep candle: wick to 1.0910, close at 1.0890 (below level)
        sweep_candle = _make_candle(
            ts=20.0, o=1.0880, h=1.0910, l=1.0875, c=1.0890, vol=3000.0
        )
        candles.append(sweep_candle)

        sweeps = engine.detect_sweeps(candles, levels)
        buy_sweeps = [s for s in sweeps if s.direction == SweepDirection.BUY_SIDE]
        assert len(buy_sweeps) >= 1
        assert buy_sweeps[0].sweep_depth_pips > 0
        assert buy_sweeps[0].wick_rejection_ratio > 0

    def test_sell_side_sweep_detected(self):
        """Wick below EQL, close above = sell-side sweep (stop hunt on longs)."""
        engine = LiquiditySweepEngine(swing_lookback=2, min_sweep_depth_pips=1.0)
        level_price = 1.0800

        levels = [
            LiquidityLevel(
                price=level_price,
                level_type=LiquidityLevelType.EQUAL_LOWS,
                touch_count=2,
                tolerance_pips=2.0,
            )
        ]

        candles = _make_flat_candles(20, base=1.0850)
        sweep_candle = _make_candle(
            ts=20.0, o=1.0820, h=1.0830, l=1.0790, c=1.0810, vol=2500.0
        )
        candles.append(sweep_candle)

        sweeps = engine.detect_sweeps(candles, levels)
        sell_sweeps = [s for s in sweeps if s.direction == SweepDirection.SELL_SIDE]
        assert len(sell_sweeps) >= 1
        assert sell_sweeps[0].sweep_depth_pips > 0

    def test_no_sweep_on_clean_breakout(self):
        """Candle closes ABOVE level = real breakout, NOT a sweep."""
        engine = LiquiditySweepEngine(swing_lookback=2, min_sweep_depth_pips=1.0)
        level_price = 1.0900

        levels = [
            LiquidityLevel(
                price=level_price,
                level_type=LiquidityLevelType.EQUAL_HIGHS,
                touch_count=2,
                tolerance_pips=2.0,
            )
        ]

        candles = _make_flat_candles(20, base=1.0850)
        # Breakout candle: closes well above level
        breakout = _make_candle(
            ts=20.0, o=1.0890, h=1.0920, l=1.0885, c=1.0915, vol=2000.0
        )
        candles.append(breakout)

        sweeps = engine.detect_sweeps(candles, levels)
        assert len(sweeps) == 0


class TestConfidenceScoring:
    """Verify confidence score computation is bounded and logical."""

    def test_confidence_bounded_0_to_1(self):
        engine = LiquiditySweepEngine()
        score = engine._compute_confidence(
            wick_ratio=0.8, depth_atr=1.0, vol_ratio=2.5, touch_count=3
        )
        assert 0.0 <= score <= 1.0

    def test_strong_sweep_higher_confidence_than_weak(self):
        engine = LiquiditySweepEngine()
        strong = engine._compute_confidence(
            wick_ratio=0.85, depth_atr=1.0, vol_ratio=2.5, touch_count=4
        )
        weak = engine._compute_confidence(
            wick_ratio=0.3, depth_atr=0.3, vol_ratio=1.1, touch_count=1
        )
        assert strong > weak

    def test_zero_inputs_give_zero_confidence(self):
        engine = LiquiditySweepEngine()
        score = engine._compute_confidence(
            wick_ratio=0.0, depth_atr=0.0, vol_ratio=0.0, touch_count=0
        )
        assert score == 0.0


class TestFullAnalysisPipeline:
    """End-to-end integration test."""

    def test_analyze_returns_valid_result(self):
        engine = LiquiditySweepEngine(swing_lookback=2)
        candles = _make_flat_candles(30, base=1.0850)
        result = engine.analyze(candles, symbol="EURUSD", timeframe="H1")

        assert isinstance(result, SweepAnalysisResult)
        assert result.symbol == "EURUSD"
        assert result.timeframe == "H1"
        assert result.evidence_weight <= 0.15  # Golden Rule #8
        assert result.sweep_bias in ("FADE_BUY", "FADE_SELL", "NEUTRAL")

    def test_evidence_weight_never_exceeds_15_percent(self):
        engine = LiquiditySweepEngine(swing_lookback=2, max_evidence_weight=0.15)
        pip = 0.0001
        candles = _make_flat_candles(30, base=1.0850)
        # Force a strong sweep scenario
        candles.append(_make_candle(30.0, 1.0880, 1.0920, 1.0870, 1.0875, vol=5000.0))
        result = engine.analyze(candles, symbol="GBPUSD", timeframe="M15")
        assert result.evidence_weight <= 0.15

    def test_insufficient_data_returns_neutral(self):
        engine = LiquiditySweepEngine(swing_lookback=5)
        candles = _make_flat_candles(3)
        result = engine.analyze(candles)
        assert result.sweep_bias == "NEUTRAL"
        assert result.evidence_weight == 0.0
'''

test_path.write_text(test_code, encoding="utf-8")
log("✅ test_liquidity_sweep_engine.py created", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 3: Run New Tests First (Fast Feedback)
# ═══════════════════════════════════════════════════════════════
log("STEP 3: Running Liquidity Sweep Engine tests...", "\033[93m")
run_cmd(
    f'"{PYTHON}" -m pytest tests/test_liquidity_sweep_engine.py -v --tb=short',
    BACKEND,
    "New sweep engine tests"
)
log("✅ All new sweep engine tests PASSED", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 4: Full Regression (285 existing + new tests)
# ═══════════════════════════════════════════════════════════════
log("STEP 4: Running FULL regression suite...", "\033[93m")
run_cmd(f'"{PYTHON}" -m pytest tests --tb=short -q', BACKEND, "Full backend regression")
log("✅ Full regression PASSED (100% GREEN)", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 5: Start Services & Run E2E + Vitest
# ═══════════════════════════════════════════════════════════════
log("STEP 5: Starting services for frontend regression...", "\033[93m")
kill_ports([8000, 5173])

backend_proc = subprocess.Popen(
    [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=str(BACKEND), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)
frontend_proc = subprocess.Popen(
    "npx vite --host 127.0.0.1 --port 5173",
    cwd=str(FRONTEND), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
)

def wait_for_url(url, headers=None, timeout=40, label="Service"):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 304):
                    print(f"  ✅ {label} UP ({round(time.time()-start, 1)}s)")
                    return True
        except Exception:
            time.sleep(1)
    return False

if not wait_for_url("http://127.0.0.1:8000/api/telemetry/cockpit", {"Authorization": "Bearer dev-secret-token"}, 40, "Backend"):
    kill_ports([8000, 5173])
    error_exit("Backend failed")
if not wait_for_url("http://127.0.0.1:5173", None, 30, "Frontend"):
    kill_ports([8000, 5173])
    error_exit("Frontend failed")

try:
    log("STEP 6: Running Vitest (16 tests)...", "\033[93m")
    run_cmd("npm run test -- --run", FRONTEND, "Vitest")
    log("✅ Vitest 16/16 PASSED", "\033[92m")

    log("STEP 7: Running Playwright E2E (4 tests)...", "\033[93m")
    run_cmd("npx playwright test", FRONTEND, "Playwright E2E")
    log("✅ Playwright 4/4 PASSED", "\033[92m")

    # ═══════════════════════════════════════════════════════════
    # STEP 8: Git Commit & Push
    # ═══════════════════════════════════════════════════════════
    log("STEP 8: Committing & Pushing Phase 2A to GitHub...", "\033[93m")
    run_cmd("git add .", ROOT, "Staging")
    run_cmd(
        'git commit -m "feat(intelligence): Phase 2A Liquidity Sweep Statistics Engine with EQH/EQL detection, sweep metrics & confidence scoring"',
        ROOT, "Committing"
    )
    run_cmd("git push origin main", ROOT, "Pushing to GitHub")
    log("✅ Pushed to GitHub!", "\033[92m")

    print("\n" + "═"*75)
    print("\033[92m🎉 PHASE 2A LIQUIDITY SWEEP ENGINE COMPLETE & VERIFIED!\033[0m")
    print("  • Engine: app/engines/intelligence/liquidity_sweep.py")
    print("  • Tests: tests/test_liquidity_sweep_engine.py")
    print("  • All regression suites: 100% GREEN")
    print("  • GitHub: Pushed to origin/main")
    print("═"*75 + "\n")

finally:
    kill_ports([8000, 5173])
