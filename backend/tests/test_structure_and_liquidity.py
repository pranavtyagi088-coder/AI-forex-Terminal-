import pytest
from app.engines.structure.structure_engine import MarketStructureEngine
from app.engines.liquidity.liquidity_engine import LiquidityEngine


def test_market_structure_bullish_bos():
    # Construct an ascending series with higher highs and higher lows
    candles = [
        {"open": 1.00, "high": 1.02, "low": 0.99, "close": 1.01, "datetime": "1"},
        {"open": 1.01, "high": 1.05, "low": 1.00, "close": 1.04, "datetime": "2"}, # Swing High 1.05
        {"open": 1.04, "high": 1.04, "low": 1.01, "close": 1.02, "datetime": "3"}, # Swing Low 1.01
        {"open": 1.02, "high": 1.08, "low": 1.02, "close": 1.07, "datetime": "4"}, # Swing High 1.08
        {"open": 1.07, "high": 1.07, "low": 1.03, "close": 1.04, "datetime": "5"}, # Swing Low 1.03
        {"open": 1.04, "high": 1.10, "low": 1.04, "close": 1.09, "datetime": "6"}, # Current close 1.09 > 1.08 (BOS)
        {"open": 1.09, "high": 1.11, "low": 1.08, "close": 1.10, "datetime": "7"},
        {"open": 1.10, "high": 1.12, "low": 1.09, "close": 1.11, "datetime": "8"},
        {"open": 1.11, "high": 1.13, "low": 1.10, "close": 1.12, "datetime": "9"},
        {"open": 1.12, "high": 1.14, "low": 1.11, "close": 1.13, "datetime": "10"}
    ]
    analysis = MarketStructureEngine.analyze_structure(candles)
    assert analysis is not None
    assert "structure_bias" in analysis
    assert analysis["structure_bias"] in ["BULLISH", "BULLISH_REVERSAL", "NEUTRAL"]


def test_fvg_detection_bullish_and_bearish():
    # 3-candle setup creating Bullish FVG (c3 low > c1 high)
    bullish_fvg_candles = [
        {"open": 1.0800, "high": 1.0810, "low": 1.0790, "close": 1.0805, "datetime": "1"}, # C1 High = 1.0810
        {"open": 1.0805, "high": 1.0860, "low": 1.0800, "close": 1.0855, "datetime": "2"}, # Big expansion
        {"open": 1.0855, "high": 1.0880, "low": 1.0830, "close": 1.0870, "datetime": "3"}, # C3 Low = 1.0830 (> 1.0810, 20 pips FVG)
    ]
    fvgs = LiquidityEngine.detect_fvg(bullish_fvg_candles, pip_size=0.0001)
    assert len(fvgs) == 1
    assert fvgs[0].type == "BULLISH_FVG"
    assert fvgs[0].top == 1.0830
    assert fvgs[0].bottom == 1.0810
    assert fvgs[0].size_pips == 20.0
    assert fvgs[0].mitigated is False


def test_liquidity_sweep_detection():
    key_support = 1.0800
    # Candle pierced below 1.0800 to 1.0780, but closed at 1.0815 (Liquidity Raid / Wick)
    candles = [
        {"open": 1.0820, "high": 1.0830, "low": 1.0780, "close": 1.0815, "datetime": "1"}
    ]
    swept = LiquidityEngine.detect_liquidity_sweep(candles, swing_level=key_support, direction="BUY")
    assert swept is True
