"""Tests for Paper Trading execution, PnL calculation, and trades API."""

import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_paper_trade_lifecycle():
    # 1. Execute BUY trade on EUR/USD
    open_payload = {
        "symbol": "EUR/USD",
        "direction": "BUY",
        "position_size_lots": 1.0,
        "entry_price": 1.1000,
        "stop_loss": 1.0950,
        "take_profit": 1.1100,
        "slippage_pips": 0.5,
    }
    response = client.post(
        "/api/trades/execute",
        json=open_payload,
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    )
    assert response.status_code == 200
    trade_data = response.json()
    assert trade_data["status"] == "success"
    trade_id = trade_data["trade_id"]
    # 1.1000 + 0.5 pips (0.00005) = 1.10005
    assert trade_data["entry_fill"] == pytest.approx(1.10005)

    # 2. Check Open Trades Endpoint
    open_resp = client.get(
        "/api/trades/open",
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    )
    assert open_resp.status_code == 200
    open_list = open_resp.json()
    assert any(t["id"] == trade_id for t in open_list)

    # 3. Close Trade at 1.1050 (Profit: ~49.5 pips * $10 - $7 commission = ~$488)
    close_payload = {
        "trade_id": trade_id,
        "symbol": "EUR/USD",
        "direction": "BUY",
        "exit_price": 1.1050,
    }
    close_resp = client.post(
        "/api/trades/close",
        json=close_payload,
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    )
    assert close_resp.status_code == 200
    close_data = close_resp.json()
    assert close_data["status"] == "success"
    assert close_data["realized_pnl_usd"] > 400.0  # Profitable trade

    # 4. Check Closed Trade History
    hist_resp = client.get(
        "/api/trades/history",
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    )
    assert hist_resp.status_code == 200
    hist_list = hist_resp.json()
    assert any(t["id"] == trade_id for t in hist_list)
