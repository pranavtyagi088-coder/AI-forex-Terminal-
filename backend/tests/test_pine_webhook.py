import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def test_receive_pine_alert_success():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "symbol": "EURUSD",
                "timeframe": "15",
                "event": "BOS_BULL",
                "price": 1.08650,
                "atr": 0.00120,
                "extBias": 1,
                "intBias": 1,
                "regime": "TREND+",
                "session": "LONDON"
            }
            response = await client.post("/api/webhooks/tradingview", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "EURUSD"
            assert data["eventType"] == "BOS_BULL"
            assert data["structure"]["regime"] == "TREND+"
            assert "chartObservedAt" in data
    run_async(run())

def test_get_latest_snapshot_success():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/webhooks/snapshots/EURUSD/15")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "EURUSD"
            assert data["price"] == 1.08650
    run_async(run())

def test_receive_pine_alert_malformed_rejected():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Missing required 'price' and 'event'
            payload = {
                "symbol": "EURUSD",
                "timeframe": "15"
            }
            response = await client.post("/api/webhooks/tradingview", json=payload)
            assert response.status_code == 422  # Unprocessable Entity
    run_async(run())
