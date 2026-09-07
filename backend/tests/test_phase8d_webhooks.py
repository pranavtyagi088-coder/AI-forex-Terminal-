import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_webhook_alert_feed_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Clear existing alerts
        await client.post("/api/webhooks/alerts/clear")

        # 2. Post Bullish Alert
        bull_payload = {
            "symbol": "GBPUSD",
            "timeframe": "15",
            "event": "BOS_BULL",
            "price": 1.2750,
            "atr": 0.0015,
            "extBias": 1,
            "intBias": 1,
            "regime": "TREND+",
            "session": "LONDON"
        }
        res1 = await client.post("/api/webhooks/tradingview", json=bull_payload)
        assert res1.status_code == 200

        # 3. Post Bearish Alert
        bear_payload = {
            "symbol": "USDJPY",
            "timeframe": "1h",
            "event": "CHUCH_BEAR",
            "price": 155.20,
            "atr": 0.25,
            "extBias": -1,
            "intBias": -1,
            "regime": "REVERSAL",
            "session": "NY"
        }
        res2 = await client.post("/api/webhooks/tradingview", json=bear_payload)
        assert res2.status_code == 200

        # 4. Fetch Alert Feed
        res_alerts = await client.get("/api/webhooks/alerts?limit=10")
        assert res_alerts.status_code == 200
        alerts = res_alerts.json()
        assert len(alerts) >= 2
        assert alerts[0]["symbol"] == "USDJPY"
        assert alerts[0]["suggested_direction"] == "SELL"
        assert alerts[1]["symbol"] == "GBPUSD"
        assert alerts[1]["suggested_direction"] == "BUY"

        # 5. Clear alerts
        res_clear = await client.post("/api/webhooks/alerts/clear")
        assert res_clear.status_code == 200
        res_empty = await client.get("/api/webhooks/alerts")
        assert len(res_empty.json()) == 0
