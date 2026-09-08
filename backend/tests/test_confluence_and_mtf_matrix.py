import pytest
from app.engines.market.confluence import ConfluenceScoringEngine, ConfluenceGrade


def test_confluence_high_grade_bullish_alignment():
    """All timeframes bullish + Value Area discount = Grade A+ Institutional Confluence."""
    bullish_daily = [
        {"open": 1.0500 + i * 0.002, "high": 1.0510 + i * 0.002, "low": 1.0490 + i * 0.002, "close": 1.0508 + i * 0.002, "volume": 5000}
        for i in range(30)
    ]
    bullish_4h = [
        {"open": 1.0700 + i * 0.001, "high": 1.0708 + i * 0.001, "low": 1.0695 + i * 0.001, "close": 1.0705 + i * 0.001, "volume": 3000}
        for i in range(30)
    ]
    bullish_1h = [
        {"open": 1.0900 + i * 0.0005, "high": 1.0905 + i * 0.0005, "low": 1.0895 + i * 0.0005, "close": 1.0902 + i * 0.0005, "volume": 1000}
        for i in range(30)
    ]

    tf_map = {"1D": bullish_daily, "4H": bullish_4h, "1H": bullish_1h}
    result = ConfluenceScoringEngine.evaluate_confluence(
        timeframe_candles=tf_map,
        proposed_direction="BUY",
        current_price=1.0700,
        symbol="EURUSD",
    )

    assert result.total_confluence_score >= 70.0
    assert result.confluence_grade in (ConfluenceGrade.A_PLUS_INSTITUTIONAL, ConfluenceGrade.B_ACCEPTABLE)
    assert result.is_aligned_with_htf is True
    assert len(result.positive_confluences) > 0


def test_confluence_low_grade_counter_trend_rejection():
    """Buying in a severe downtrend results in REJECT_NO_CONFLUENCE."""
    bearish_daily = [
        {"open": 1.1500 - i * 0.002, "high": 1.1510 - i * 0.002, "low": 1.1490 - i * 0.002, "close": 1.1492 - i * 0.002, "volume": 5000}
        for i in range(30)
    ]
    tf_map = {"1D": bearish_daily}
    result = ConfluenceScoringEngine.evaluate_confluence(
        timeframe_candles=tf_map,
        proposed_direction="BUY",
        current_price=1.0900,
        symbol="EURUSD",
    )

    assert result.total_confluence_score < 50.0
    assert result.confluence_grade == ConfluenceGrade.REJECT_NO_CONFLUENCE
    assert len(result.negative_frictions) > 0
