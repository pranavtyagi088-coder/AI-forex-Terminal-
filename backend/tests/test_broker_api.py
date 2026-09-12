import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

AUTH_HEADERS = {"Authorization": "Bearer dev-secret-token"}


@pytest.mark.asyncio
async def test_broker_account_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/trades/broker/account", headers=AUTH_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "account_id" in data
        assert data["balance"] == 100000.0
        assert data["is_connected"] is True
        assert data["latency_ms"] > 0.0


@pytest.mark.asyncio
async def test_broker_positions_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/trades/broker/positions", headers=AUTH_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "positions" in data
        assert isinstance(data["positions"], list)


@pytest.mark.asyncio
async def test_stage_and_approve_live_broker_execution():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Stage proposal
        stage_payload = {
            "request": {
                "symbol": "EURUSD",
                "direction": "BUY",
                "entry_price": 1.0850,
                "stop_loss": 1.0800,
                "take_profit": 1.0950,
                "account_balance": 100000.0,
                "risk_per_trade_pct": 1.0,
                "current_spread_pips": 1.0,
            },
            "idempotency_key": "API-TEST-STAGE-001",
            "max_slippage_pips": 1.0,
        }
        stage_res = await client.post("/api/trades/proposals/stage", json=stage_payload, headers=AUTH_HEADERS)
        assert stage_res.status_code == 200
        prop = stage_res.json()
        assert prop["status"] == "PENDING_APPROVAL"
        proposal_id = prop["proposal_id"]

        # 2. Approve via Broker Bridge (LIVE mode)
        approve_payload = {
            "current_market_price": 1.0850,
            "execution_mode": "LIVE",
        }
        approve_res = await client.post(
            f"/api/trades/proposals/{proposal_id}/approve",
            json=approve_payload,
            headers=AUTH_HEADERS,
        )
        assert approve_res.status_code == 200
        exec_data = approve_res.json()
        assert exec_data["status"] == "success"
        assert exec_data["execution_mode"] == "LIVE_BROKER"
        assert exec_data["ticket"].startswith("MT5-")
        assert exec_data["fill_price"] > 0.0


@pytest.mark.asyncio
async def test_emergency_close_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/trades/broker/emergency-close",
            json={"reason": "Test Risk Intercept"},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
