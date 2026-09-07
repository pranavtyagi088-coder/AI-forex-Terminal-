import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.trade import Trade
from app.engines.strategy.decay_detector import DecayDetector

client = TestClient(app)
AUTH_HEADERS = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}

def test_decay_detector_healthy_sequence():
    trades = [
        Trade(status="CLOSED", pnl=150.0, realized_r=1.5),
        Trade(status="CLOSED", pnl=200.0, realized_r=2.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=180.0, realized_r=1.8),
        Trade(status="CLOSED", pnl=120.0, realized_r=1.2),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
    ]
    metrics = DecayDetector.compute_metrics(trades, current_lifecycle="ACTIVE")
    assert metrics.total_trades == 6
    assert metrics.winning_trades == 4
    assert metrics.win_rate > 60.0
    assert metrics.avg_realized_r > 0
    assert metrics.lifecycle_status == "ACTIVE"
    assert len(metrics.decay_warnings) == 0

def test_decay_detector_degraded_on_severe_losses():
    trades = [
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
        Trade(status="CLOSED", pnl=-100.0, realized_r=-1.0),
    ]
    metrics = DecayDetector.compute_metrics(trades, current_lifecycle="ACTIVE")
    assert metrics.win_rate == 0.0
    assert metrics.avg_realized_r == -1.0
    assert metrics.consecutive_losses == 6
    assert metrics.lifecycle_status in ["CAUTION", "DEGRADED", "RETIRED"]
    assert len(metrics.decay_warnings) > 0

def test_performance_api_overview_endpoint():
    res = client.get("/api/performance/overview", headers=AUTH_HEADERS)
    assert res.status_code == 200
    data = res.json()
    assert "strategies" in data
    assert data["count"] > 0
    assert "win_rate" in data["strategies"][0]

def test_performance_api_strategy_detail_and_eval():
    overview = client.get("/api/performance/overview", headers=AUTH_HEADERS).json()
    strat_id = overview["strategies"][0]["strategy_id"]

    # 1. Detail endpoint
    detail_res = client.get(f"/api/performance/{strat_id}", headers=AUTH_HEADERS)
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert detail_data["strategy_id"] == str(strat_id)
    assert "metrics" in detail_data

    # 2. Evaluate endpoint
    eval_res = client.post(f"/api/performance/evaluate/{strat_id}", headers=AUTH_HEADERS)
    assert eval_res.status_code == 200
    eval_data = eval_res.json()
    assert "updated_lifecycle_status" in eval_data
