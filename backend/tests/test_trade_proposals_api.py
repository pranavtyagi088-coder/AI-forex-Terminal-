import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)
AUTH_HEADER = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}


def test_stage_proposal_api_success():
    payload = {
        "request": {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "account_balance": 100000.0,
            "risk_per_trade_pct": 1.0,
            "circuit_breaker_state": "NORMAL",
        },
        "idempotency_key": "api-test-key-1",
        "max_slippage_pips": 1.0,
    }
    response = client.post("/api/trades/proposals/stage", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PENDING_APPROVAL"
    assert data["proposal_id"].startswith("PROP-")
    assert data["position_size_lots"] > 0


def test_stage_proposal_idempotency_replay():
    payload = {
        "request": {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "account_balance": 100000.0,
        },
        "idempotency_key": "api-replay-key-999",
    }
    res1 = client.post("/api/trades/proposals/stage", json=payload)
    res2 = client.post("/api/trades/proposals/stage", json=payload)
    assert res1.json()["proposal_id"] == res2.json()["proposal_id"]


def test_approve_proposal_with_slippage_rejection():
    payload = {
        "request": {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "account_balance": 100000.0,
        },
        "idempotency_key": "api-slip-test-1",
        "max_slippage_pips": 0.5,
    }
    stage_res = client.post("/api/trades/proposals/stage", json=payload)
    prop_id = stage_res.json()["proposal_id"]

    # Price moved 2 pips -> 1.1002 (beyond 0.5 max slippage)
    approve_res = client.post(
        f"/api/trades/proposals/{prop_id}/approve",
        json={"current_market_price": 1.1002},
        headers=AUTH_HEADER,
    )
    assert approve_res.status_code == 422
    assert "Slippage limit breached" in approve_res.json()["detail"]
