import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.engines.backtest.engine import DeterministicBacktestEngine, generate_synthetic_ohlcv


@pytest.mark.asyncio
async def test_backtest_drawdown_curve_and_friction():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "strategy": "trend_continuation",
            "initial_capital": 10000.0,
            "risk_per_trade": 1.0,
            "slippage_pips": 1.0,
            "commission_per_lot": 10.0,
            "random_seed": 12345
        }
        res = await client.post("/api/backtest/run", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["equity_curve"]) > 50
        assert len(data["drawdown_curve"]) == len(data["equity_curve"])
        assert data["slippage_pips_used"] == 1.0
        assert data["commission_per_lot_used"] == 10.0
        assert data["is_metrics"] is not None
        assert data["oos_metrics"] is not None


@pytest.mark.asyncio
async def test_strategy_comparison_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "symbol": "EUR/USD",
            "timeframe": "1h",
            "compare_strategies": ["trend_continuation", "mean_reversion"],
            "initial_capital": 10000.0,
            "risk_per_trade": 1.0,
            "random_seed": 42
        }
        res = await client.post("/api/backtest/compare", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert len(data["comparisons"]) == 2
        assert data["comparisons"][0]["strategy"] == "trend_continuation"
        assert data["comparisons"][1]["strategy"] == "mean_reversion"
        assert len(data["comparisons"][0]["drawdown_curve"]) > 0
