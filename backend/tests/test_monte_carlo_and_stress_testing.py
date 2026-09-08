import pytest
from app.engines.analytics.monte_carlo import MonteCarloEngine, MonteCarloSimulationResult
from app.engines.risk.stress_testing import PortfolioStressEngine, ShockScenarioType
from app.engines.risk.correlation import OpenPositionInput


def test_monte_carlo_simulation_statistical_bounds():
    """Monte Carlo engine runs 1,000 iterations and generates valid percentile cones."""
    pnls = [1200.0, -500.0, 1500.0, -400.0, 800.0, -600.0, 2000.0, -500.0]
    res: MonteCarloSimulationResult = MonteCarloEngine.run_simulation(
        trade_pnls=pnls,
        initial_capital=100000.0,
        n_iterations=1000,
        sample_horizon_trades=50,
        max_drawdown_ruin_pct=10.0,
        random_seed=42,
    )

    assert res.iterations_run == 1000
    assert res.median_final_equity > 100000.0
    assert res.optimistic_95th_pct_equity >= res.median_final_equity
    assert res.pessimistic_5th_pct_equity <= res.median_final_equity
    assert res.max_drawdown_95th_pct >= 0.0
    assert len(res.confidence_cone.percentile_50th) > 0
    assert res.probability_of_ruin_pct <= 5.0  # Profitable edge should have low ruin prob


def test_monte_carlo_detects_high_risk_of_ruin_on_losing_edge():
    """Losing strategy produces high Probability of Ruin and fails prop firm safety."""
    heavy_loss_pnls = [-1500.0, -2000.0, 500.0, -1800.0, -1200.0]
    res = MonteCarloEngine.run_simulation(
        trade_pnls=heavy_loss_pnls,
        initial_capital=100000.0,
        n_iterations=500,
        sample_horizon_trades=50,
        max_drawdown_ruin_pct=10.0,
        random_seed=42,
    )

    assert res.probability_of_ruin_pct > 1.0
    assert res.is_prop_firm_safe is False
    assert res.max_drawdown_95th_pct >= 10.0


def test_portfolio_stress_engine_catastrophe_shocks():
    """Portfolio stress engine evaluates flash crashes, gaps, and correlation collapse."""
    open_positions = [
        OpenPositionInput(symbol="EURUSD", direction="BUY", risk_usd=1000.0, risk_pct=1.0),
        OpenPositionInput(symbol="GBPUSD", direction="BUY", risk_usd=1000.0, risk_pct=1.0),
    ]

    report = PortfolioStressEngine.stress_test_portfolio(
        account_balance=100000.0,
        open_positions=open_positions,
    )

    assert report.total_open_positions == 2
    assert len(report.scenarios) == 3
    assert report.worst_case_drawdown_pct > 0.0

    scenario_types = [s.scenario_type for s in report.scenarios]
    assert ShockScenarioType.FLASH_CRASH_SPREAD_BLOWOUT in scenario_types
    assert ShockScenarioType.WEEKEND_GAP_SHOCK in scenario_types
    assert ShockScenarioType.CORRELATION_CONTAGION_COLLAPSE in scenario_types


def test_portfolio_stress_engine_zero_open_positions():
    """Zero open positions reports complete resilience."""
    report = PortfolioStressEngine.stress_test_portfolio(account_balance=100000.0, open_positions=[])
    assert report.total_open_positions == 0
    assert report.worst_case_drawdown_pct == 0.0
    assert report.is_resilient_to_black_swan is True
