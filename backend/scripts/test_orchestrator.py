import asyncio
import pytest
from app.engines.intelligence.orchestrator import MarketIntelligenceOrchestrator

@pytest.mark.asyncio
async def test_orchestration():
    orchestrator = MarketIntelligenceOrchestrator()
    res1 = await orchestrator.run_analysis(symbol="EUR/USD", timeframe="1H", direction="BUY")
    assert res1["symbol"] == "EUR/USD"

if __name__ == "__main__":
    asyncio.run(test_orchestration())
