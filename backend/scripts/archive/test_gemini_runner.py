import asyncio
from app.core.config import settings
from app.services.ai.gemini_provider import GeminiProvider
from app.services.ai.chart_analyzer import ChartAnalyzer

async def run_all_tests():
    print("\n=======================================================")
    print("       AI FOREX TERMINAL - GEMINI INTEGRATION AUDIT    ")
    print("=======================================================")

    # TEST 1: Config
    print("\n[TEST 1] Checking Environment Configuration...")
    has_gemini_key = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY.strip()) > 5)
    print(f"  - Configured Model: {settings.GEMINI_MODEL}")
    print(f"  - Gemini API Key Loaded: {'[YES - Configured]' if has_gemini_key else '[NO - Missing in .env]'}")
    assert has_gemini_key, "GEMINI_API_KEY is missing or empty in .env"
    print("  -> TEST 1 PASSED")

    # TEST 2 & 3: Direct API Connectivity & Structured JSON
    print("\n[TEST 2 & 3] Testing Direct Gemini Connectivity & JSON Schema Output...")
    provider = GeminiProvider()
    prompt = (
        "Forex analysis test for EUR/USD price 1.0850. "
        "Return valid JSON strictly with keys: trend_direction, bias, confidence, support_levels, resistance_levels, why_reasons."
    )
    result = await provider.analyze_chart(prompt=prompt)
    print(f"  - Response Trend: {result.get('trend_direction')}")
    print(f"  - Response Bias: {result.get('bias')}")
    print(f"  - Response Confidence: {result.get('confidence')}")
    print(f"  - Support Levels: {result.get('support_levels')}")
    print(f"  - Resistance Levels: {result.get('resistance_levels')}")
    
    assert "trend_direction" in result, "Missing trend_direction in response"
    assert "bias" in result, "Missing bias in response"
    print("  -> TEST 2 & 3 PASSED")

    # TEST 4: Multimodal Chart Analysis (1x1 Base64 PNG)
    print("\n[TEST 4] Testing Multimodal (Image + Prompt) Analysis...")
    mock_base64_png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    analyzer = ChartAnalyzer()
    multimodal_result = await analyzer.analyze(
        base64_image=mock_base64_png,
        market_context={"pair": "EUR/USD", "current_price": 1.0850}
    )
    print(f"  - Provider Used: {multimodal_result.get('provider_used')}")
    print(f"  - Bias: {multimodal_result.get('bias')}")
    assert "gemini" in multimodal_result.get("provider_used", "").lower()
    print("  -> TEST 4 PASSED")

    # TEST 5 & 6: Safe Fallback Verification (Zero Crash Simulation)
    print("\n[TEST 5 & 6] Testing Fallback Safety (Simulating Invalid API Key)...")
    broken_analyzer = ChartAnalyzer()
    broken_analyzer.gemini = GeminiProvider(api_key="invalid_test_key_xyz", model="gemini-2.5-flash")
    broken_analyzer.openai_key = None  # OpenAI disabled
    
    fallback_result = await broken_analyzer.analyze(
        market_context={"pair": "EUR/USD", "current_price": 1.0850}
    )
    print(f"  - Fallback Provider Used: {fallback_result.get('provider_used')}")
    print(f"  - Safety No-Trade Warning: {fallback_result.get('no_trade_warning')}")
    assert fallback_result["provider_used"] == "deterministic_fallback"
    assert fallback_result["no_trade_warning"] is True
    print("  -> TEST 5 & 6 PASSED")

    print("\n=======================================================")
    print("   ALL TESTS PASSED: GEMINI IS FULLY OPERATIONAL!       ")
    print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
