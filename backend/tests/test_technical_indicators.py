import numpy as np
import pandas as pd
import pytest
from app.engines.indicators.technical import compute_technical_snapshot

def _make_ohlcv(closes: list[float]) -> pd.DataFrame:
    closes = np.array(closes)
    highs = closes + 0.15
    lows = closes - 0.15
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    return pd.DataFrame({
        "open": opens, "high": highs, "low": lows,
        "close": closes, "volume": np.full(len(closes), 1000.0),
    })

def test_uptrend_is_detected_as_bullish():
    n = 120
    rng = np.random.default_rng(42)
    closes = 100 + np.cumsum(np.full(n, 0.25)) + rng.normal(0, 0.05, n)
    df = _make_ohlcv(list(closes))
    snap = compute_technical_snapshot(df)
    assert snap.trend_direction == "bullish"
    assert snap.ema_fast > snap.ema_slow
    assert snap.trend_strength > 20

def test_downtrend_is_detected_as_bearish():
    n = 120
    rng = np.random.default_rng(7)
    closes = 100 - np.cumsum(np.full(n, 0.25)) + rng.normal(0, 0.05, n)
    df = _make_ohlcv(list(closes))
    snap = compute_technical_snapshot(df)
    assert snap.trend_direction == "bearish"
    assert snap.ema_fast < snap.ema_slow

def test_choppy_range_is_not_forced_into_a_trend():
    n = 120
    rng = np.random.default_rng(3)
    closes = 100 + rng.normal(0, 0.3, n)
    df = _make_ohlcv(list(closes))
    snap = compute_technical_snapshot(df)
    assert snap.trend_direction == "sideways"

def test_raises_on_insufficient_bars():
    df = _make_ohlcv([100.0 + i * 0.1 for i in range(10)])
    with pytest.raises(ValueError, match="at least 60 bars"):
        compute_technical_snapshot(df)

def test_swing_levels_bracket_price_in_a_ranging_market():
    n = 120
    rng = np.random.default_rng(11)
    closes = 100 + np.sin(np.linspace(0, 8 * np.pi, n)) * 2 + rng.normal(0, 0.05, n)
    df = _make_ohlcv(list(closes))
    snap = compute_technical_snapshot(df)
    assert len(snap.swing_highs) > 0
    assert len(snap.swing_lows) > 0
