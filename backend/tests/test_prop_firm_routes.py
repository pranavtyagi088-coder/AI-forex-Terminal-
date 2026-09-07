import asyncio
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

# Isolated loop runner to bypass pytest-asyncio plugin bugs on Python 3.14
def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def test_get_prop_firm_profile():
    async def run():
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/prop-firm-profiles/funding_pips_100k")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == "funding_pips_100k"
            assert "dailyDrawdownPct" in data
    run_async(run())

def test_get_account_state():
    async def run():
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/accounts/acc_test_001/state")
            assert response.status_code == 200
            data = response.json()
            assert data["accountId"] == "acc_test_001"
            assert data["currentBalance"] == 100000.0
    run_async(run())

def test_perform_trade_check_allowed():
    async def run():
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "pair": "EURUSD",
                "orderType": "BUY",
                "lotSize": 2.0,
                "stopLossPips": 10.0,
                "entryPrice": 1.08500
            }
            response = await client.post("/api/accounts/acc_test_001/trade-check", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["allowed"] is True
            assert data["riskAmountUsd"] == 200.0
    run_async(run())

def test_get_account_health():
    async def run():
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/accounts/acc_test_001/health")
            assert response.status_code == 200
            data = response.json()
            assert data["score"] == 100.0
            assert data["status"] == "HEALTHY"
    run_async(run())
