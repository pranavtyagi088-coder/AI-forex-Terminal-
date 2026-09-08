import pytest
from app.engines.market.volume_profile import VolumeProfileEngine, VolumeProfileResult
from app.engines.market.regime import MarketRegimeDetector, MarketRegimeType


def test_volume_profile_poc_vah_val_calculation():
    """Volume Profile engine computes accurate POC, VAH, and VAL within 70% value area."""
    # Synthetic candles with clustered volume around 1.0800
    candles = [
        {"open": 1.0750, "high": 1.0780, "low": 1.0740, "close": 1.0770, "volume": 500},
        {"open": 1.0770, "high": 1.0820, "low": 1.0765, "close": 1.0805, "volume": 3500},  # Heavy POC volume
        {"open": 1.0800, "high": 1.0815, "low": 1.0790, "close": 1.0800, "volume": 4000},  # Heavy POC volume
        {"open": 1.0805, "high": 1.0860, "low": 1.0800, "close": 1.0850, "volume": 800},
        {"open": 1.0850, "high": 1.0890, "low": 1.0840, "close": 1.0880, "volume": 300},
    ]

    profile: VolumeProfileResult = VolumeProfileEngine.compute_profile(candles, n_bins=20)

    assert profile.total_volume > 0.0
    assert profile.poc_price > 1.0780 and profile.poc_price < 1.0830
    assert profile.vah_price >= profile.poc_price
    assert profile.val_price <= profile.poc_price
    assert profile.provenance_tag == "TICK_VOLUME_PROXY"
    assert len(profile.price_levels) > 0


def test_volume_profile_empty_or_flat_candles():
    """Volume Profile handles empty or flat zero-range candles safely."""
    flat_candles = [{"open": 1.0800, "high": 1.0800, "low": 1.0800, "close": 1.0800, "volume": 100} for _ in range(10)]
    res = VolumeProfileEngine.compute_profile(flat_candles)
    assert res.poc_price == 1.0800
    assert res.vah_price == 1.0800


def test_market_regime_bullish_trending():
    """Market regime detector identifies strong bullish trending expansion."""
    candles = [
        {"open": 1.0500 + i * 0.001, "high": 1.0505 + i * 0.001, "low": 1.0495 + i * 0.001, "close": 1.0503 + i * 0.001}
        for i in range(30)
    ]
    res = MarketRegimeDetector.classify_regime(candles, symbol="EURUSD")
    assert res.regime in (MarketRegimeType.TRENDING_BULLISH_EXPANSION, MarketRegimeType.VOLATILITY_EXPANSION)
    assert res.is_safe_for_trading is True
    assert res.confidence_score >= 50.0


def test_market_regime_insufficient_bars_fail_closed():
    """Fewer than minimum required bars returns CHOPPY_NO_TRADE safely."""
    res = MarketRegimeDetector.classify_regime([{"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}], symbol="EURUSD")
    assert res.regime == MarketRegimeType.CHOPPY_NO_TRADE
    assert res.is_safe_for_trading is False
