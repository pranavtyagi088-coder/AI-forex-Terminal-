import pytest
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from app.main import app
from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.models.trade import Trade
from app.engines.strategy.decay_sync import build_decay_map_from_db
from app.engines.intelligence.orchestrator import MarketIntelligenceOrchestrator


@pytest.mark.asyncio
async def test_journal_pagination_offset_limit():
    await init_db()
    async with AsyncSessionLocal() as session:
        for i in range(5):
            t = Trade(
                symbol="EUR/USD",
                timeframe="1h",
                strategy_name="Trend Continuation / BOS Pullback",
                direction="BUY",
                position_size_lots=0.1,
                status="CLOSED",
                result="WIN" if i % 2 == 0 else "LOSS",
                pnl=50.0 if i % 2 == 0 else -30.0,
                opened_at=datetime.now(timezone.utc),
                closed_at=datetime.now(timezone.utc)
            )
            session.add(t)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/journal/trades?limit=2&offset=0")
        assert res.status_code == 200
        items_page1 = res.json()
        assert len(items_page1) == 2

        res2 = await client.get("/api/journal/trades?limit=2&offset=2")
        assert res2.status_code == 200
        items_page2 = res2.json()
        assert len(items_page2) == 2
        assert items_page1[0]["id"] != items_page2[0]["id"]


@pytest.mark.asyncio
async def test_db_decay_sync_detects_severe_losses():
    await init_db()
    async with AsyncSessionLocal() as session:
        for _ in range(8):
            t = Trade(
                symbol="EUR/USD",
                strategy_name="Mean Reversion (RSI/Range)",
                direction="BUY",
                status="CLOSED",
                result="LOSS",
                pnl=-100.0,
                realized_r=-1.0,
                opened_at=datetime.now(timezone.utc),
                closed_at=datetime.now(timezone.utc)
            )
            session.add(t)
        await session.commit()

        decay_map = await build_decay_map_from_db(session)
        assert "Mean Reversion (RSI/Range)" in decay_map
        assert decay_map["Mean Reversion (RSI/Range)"] in ["DEGRADED", "WATCH", "SUSPENDED"]


@pytest.mark.asyncio
async def test_orchestrator_integrates_db_decay():
    await init_db()
    async with AsyncSessionLocal() as session:
        orchestrator = MarketIntelligenceOrchestrator()
        result = await orchestrator.run_analysis(
            symbol="EUR/USD",
            timeframe="15",
            direction="BUY",
            db=session
        )
        assert result["id"] is not None
        assert "strategy_intelligence" in result
        assert "best_strategy" in result["strategy_intelligence"]
        assert "strategy_ranking" in result["strategy_intelligence"]
        assert len(result["strategy_intelligence"]["strategy_ranking"]) >= 5
