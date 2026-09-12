from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
bt_file = ROOT / "backend/tests/test_broker_api.py"

clean_test_file = '''import pytest
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
            "max_slippage_pips": 2.0,
        }
        res = await client.post("/api/trades/proposals/stage", json=stage_payload, headers=AUTH_HEADERS)
        assert res.status_code == 200
        proposal = res.json()
        assert proposal["proposal_id"] is not None
        assert proposal["status"] in ["APPROVED", "PENDING_APPROVAL", "STAGED"]
        proposal_id = proposal["proposal_id"]

        # 2. Approve and Execute via Live Broker Adapter
        approve_payload = {
            "idempotency_key": "API-TEST-APPROVE-001",
            "current_market_price": 1.0851,
            "execution_mode": "LIVE",
        }
        approve_res = await client.post(
            f"/api/trades/proposals/{proposal_id}/approve",
            json=approve_payload,
            headers=AUTH_HEADERS,
        )
        assert approve_res.status_code == 200
        exec_data = approve_res.json()
        assert exec_data["status"] == "SUCCESS"
        assert exec_data["broker_ticket"] is not None
        assert exec_data["entry_fill"] > 0


@pytest.mark.asyncio
async def test_emergency_close_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/trades/broker/emergency-close",
            json={"reason": "TEST_ADMIN_TRIGGER"},
            headers=AUTH_HEADERS,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert "liquidated_tickets" in data or "closed_ticket" in data


@pytest.mark.asyncio
async def test_list_and_reject_proposal():
    """Verify /proposals list endpoint and /proposals/{id}/reject workflow."""
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
            "idempotency_key": "API-TEST-LIST-001",
            "max_slippage_pips": 2.0,
        }
        stage_res = await client.post("/api/trades/proposals/stage", json=stage_payload, headers=AUTH_HEADERS)
        assert stage_res.status_code == 200
        proposal_id = stage_res.json()["proposal_id"]

        # 2. List all proposals
        list_res = await client.get("/api/trades/proposals", headers=AUTH_HEADERS)
        assert list_res.status_code == 200
        data = list_res.json()
        assert "proposals" in data
        assert any(p["proposal_id"] == proposal_id for p in data["proposals"])

        # 3. Reject proposal
        rej_res = await client.post(f"/api/trades/proposals/{proposal_id}/reject", headers=AUTH_HEADERS)
        assert rej_res.status_code == 200
        assert rej_res.json()["status"] == "REJECTED"
'''

bt_file.write_text(clean_test_file, encoding="utf-8")
print("[SUCCESS] backend/tests/test_broker_api.py aligned to async client pattern.")
