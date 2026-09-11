"""
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
