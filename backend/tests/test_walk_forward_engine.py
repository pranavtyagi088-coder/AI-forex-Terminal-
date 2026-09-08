import pytest
from app.engines.backtest.engine import DeterministicBacktestEngine, generate_synthetic_ohlcv, BacktestResult
from app.engines.backtest.walk_forward import WalkForwardValidator, WalkForwardMetrics
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_walk_forward_robust_strategy_grading():
    """Strategy with high persistence between IS and OOS receives ROBUST grade."""
    is_res = BacktestResult(
        total_trades=20, winning_trades=12, losing_trades=8,
        win_rate=60.0, profit_factor=2.0, expectancy_r=0.6, expectancy_usd=600.0,
        max_drawdown=500.0, max_drawdown_pct=5.0, net_profit=4000.0, net_profit_pct=40.0,
        sharpe_ratio=1.8, avg_rr=1.5, consecutive_losses=2, total_bars=350,
        trades=[], equity_curve=[], drawdown_curve=[],
    )
    oos_res = BacktestResult(
        total_trades=10, winning_trades=6, losing_trades=4,
        win_rate=60.0, profit_factor=1.8, expectancy_r=0.55, expectancy_usd=550.0,
        max_drawdown=300.0, max_drawdown_pct=6.0, net_profit=1800.0, net_profit_pct=18.0,
        sharpe_ratio=1.6, avg_rr=1.4, consecutive_losses=2, total_bars=150,
        trades=[], equity_curve=[], drawdown_curve=[],
    )

    metrics: WalkForwardMetrics = WalkForwardValidator.evaluate_is_oos(is_res, oos_res)
    assert metrics.robustness_grade in ("ROBUST", "ACCEPTABLE")
    assert metrics.is_overfit_suspect is False
    assert metrics.wfe_score_pct >= 65.0
    assert metrics.profit_factor_retention_pct >= 70.0


def test_walk_forward_overfit_strategy_detection():
    """Strategy that collapses in OOS receives OVERFIT grade with suspect flag."""
    is_res = BacktestResult(
        total_trades=30, winning_trades=25, losing_trades=5,
        win_rate=83.3, profit_factor=4.5, expectancy_r=1.2, expectancy_usd=1200.0,
        max_drawdown=200.0, max_drawdown_pct=2.0, net_profit=8000.0, net_profit_pct=80.0,
        sharpe_ratio=2.5, avg_rr=2.0, consecutive_losses=1, total_bars=350,
        trades=[], equity_curve=[], drawdown_curve=[],
    )
    oos_res = BacktestResult(
        total_trades=15, winning_trades=4, losing_trades=11,
        win_rate=26.7, profit_factor=0.4, expectancy_r=-0.4, expectancy_usd=-400.0,
        max_drawdown=1500.0, max_drawdown_pct=15.0, net_profit=-2000.0, net_profit_pct=-20.0,
        sharpe_ratio=-1.2, avg_rr=0.5, consecutive_losses=5, total_bars=150,
        trades=[], equity_curve=[], drawdown_curve=[],
    )

    metrics: WalkForwardMetrics = WalkForwardValidator.evaluate_is_oos(is_res, oos_res)
    assert metrics.robustness_grade == "OVERFIT"
    assert metrics.is_overfit_suspect is True
    assert metrics.wfe_score_pct < 35.0


def test_rolling_walk_forward_multi_window():
    """Multi-window rolling walk-forward generates window slices."""
    df = generate_synthetic_ohlcv(n_bars=300, seed=42)
    engine = DeterministicBacktestEngine(symbol="EURUSD", initial_capital=10000.0)
    windows = WalkForwardValidator.run_rolling_walk_forward(df, engine, n_windows=3)

    assert len(windows) > 0
    for w in windows:
        assert w.window_wfe_pct >= 0.0
        assert w.train_bars > 0
        assert w.test_bars > 0


def test_api_backtest_run_includes_walk_forward_metrics():
    """POST /api/backtest/run returns full walk_forward_metrics block."""
    resp = client.post("/api/backtest/run", json={
        "symbol": "EURUSD",
        "timeframe": "1h",
        "strategy": "trend_continuation",
        "initial_capital": 10000.0,
        "risk_per_trade": 1.0,
        "bars_count": 300,
        "random_seed": 42,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "walk_forward_metrics" in data
    assert data["walk_forward_metrics"] is not None
    assert "robustness_grade" in data["walk_forward_metrics"]
    assert "wfe_score_pct" in data["walk_forward_metrics"]
