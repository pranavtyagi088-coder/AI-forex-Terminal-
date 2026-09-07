import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.engines.backtest.engine import DeterministicBacktestEngine

client = TestClient(app)

def make_test_dataframe(bars: int = 200) -> pd.DataFrame:
    np.random.seed(42)
    t = np.linspace(0, 8 * np.pi, bars)
    wave = np.sin(t) * 0.0120 + np.linspace(0, 0.0080, bars)
    closes = 1.0850 + wave
    highs = closes + 0.0015
    lows = closes - 0.0015
    opens = np.roll(closes, 1)
    opens[0] = 1.0850
    volumes = [1000] * bars
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes
    })

def test_backtest_engine_simulates_realistic_trades():
    df = make_test_dataframe(150)
    engine = DeterministicBacktestEngine(
        symbol="EUR/USD",
        initial_balance=10000.0,
        risk_percent=1.0,
        slippage_pips=0.5,
        commission_per_lot=7.0
    )
    result = engine.run_simulation(df)
    assert "metrics" in result
    assert "equity_curve" in result
    assert "trades" in result

    m = result["metrics"]
    assert m["initial_balance"] == 10000.0
    assert m["total_trades"] > 0
    assert 0.0 <= m["win_rate"] <= 100.0
    assert m["max_drawdown_pct"] >= 0.0

def test_backtest_api_run_endpoint():
    headers = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    payload = {
        "symbol": "EUR/USD",
        "timeframe": "1H",
        "initial_balance": 10000.0,
        "risk_percent": 1.0,
        "bars_count": 250,
        "slippage_pips": 0.5,
        "commission_per_lot": 7.0,
        "split_oos": True
    }
    response = client.post("/api/backtest/run", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EUR/USD"
    assert "overall_metrics" in data
    assert data["overall_metrics"]["total_trades"] > 0
    assert "in_sample_metrics" in data
    assert "out_of_sample_metrics" in data
    assert len(data["equity_curve"]) > 0

def test_backtest_api_history_endpoint():
    headers = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    response = client.get("/api/backtest/history", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
