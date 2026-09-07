import pytest
from unittest.mock import patch
from app.services.ai.vision_adapter import validate_base64_image
from app.services.ai.chart_analyzer import ChartAnalyzer
from app.engines.intelligence.orchestrator import MarketIntelligenceOrchestrator


def test_corrupt_base64_image_rejected():
    is_valid, mime, err = validate_base64_image("invalid_not_base64!!!")
    assert is_valid is False
    assert "Invalid base64" in err


def test_unsupported_file_format_rejected():
    import base64
    fake_txt_bytes = b"Hello, this is just plain text, not a chart image."
    fake_b64 = base64.b64encode(fake_txt_bytes).decode("utf-8")
    is_valid, mime, err = validate_base64_image(fake_b64)
    assert is_valid is False
    assert "Unsupported image format" in err


def test_valid_png_magic_bytes_accepted():
    import base64
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    png_b64 = base64.b64encode(png_bytes).decode("utf-8")
    is_valid, mime, err = validate_base64_image(png_b64)
    assert is_valid is True
    assert mime == "image/png"
    assert err is None


@pytest.mark.asyncio
async def test_ai_provider_timeout_falls_back_gracefully():
    analyzer = ChartAnalyzer()
    with patch.object(analyzer.gemini, "analyze_chart", side_effect=TimeoutError("AI Gateway Timeout")):
        result = await analyzer.analyze(
            base64_image=None,
            market_context={
                "symbol": "EUR/USD",
                "timeframe": "1h",
                "direction": "BUY",
                "trend": "BULLISH",
                "rsi": 55.0,
                "atr": 0.0015,
                "regime": "TRENDING_UP"
            }
        )
        assert result is not None
        assert "confidence" in result
        assert "bias" in result


@pytest.mark.asyncio
async def test_orchestrator_handles_market_data_failure_safely():
    with patch("app.services.market.data_service.MarketDataService.get_price", return_value=1.0850), \
         patch("app.services.market.data_service.MarketDataService.get_candles", return_value=[]):
        orchestrator = MarketIntelligenceOrchestrator()
        result = await orchestrator.run_analysis(
            symbol="EUR/USD",
            timeframe="1h",
            direction="BUY",
            account_balance=10000.0,
            risk_percent=1.0
        )
        assert result is not None
        assert "score_total" in result
        assert "position_sizing" in result
        assert result["direction"] in ["BUY", "SELL", "NO_TRADE"]
