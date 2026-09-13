import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.engines.analytics.metrics import (
    QuantitativeAnalyticsEngine,
    RollingPerformanceMetrics,
    SlippagePostMortem,
)
from app.engines.analytics.rebalancer import (
    AdaptiveWeightRebalancer,
    StrategyWeightAllocation,
)

AUTH_HEADERS = {"Authorization": "Bearer dev-secret-token"}


def test_empty_metrics_fail_safe():
    metrics = QuantitativeAnalyticsEngine.calculate_rolling_metrics([])
    assert metrics.total_trades == 0
    assert metrics.win_rate_pct == 0.0
    assert metrics.profit_factor == 0.0
    assert metrics.sharpe_ratio == 0.0
    assert metrics.sortino_ratio == 0.0
    assert metrics.calmar_ratio == 0.0
    assert metrics.is_statistically_significant is False


def test_rolling_metrics_profitable_distribution():
    # 8 wins of +$500, 2 losses of -$200
    pnls = [500.0, 500.0, -200.0, 500.0, 500.0, -200.0, 500.0, 500.0, 500.0, 500.0]
    r_multiples = [2.0, 2.0, -1.0, 2.0, 2.0, -1.0, 2.0, 2.0, 2.0, 2.0]

    metrics = QuantitativeAnalyticsEngine.calculate_rolling_metrics(pnls, r_multiples)
    assert metrics.total_trades == 10
    assert metrics.winning_trades == 8
    assert metrics.losing_trades == 2
    assert metrics.win_rate_pct == 80.0
    assert metrics.profit_factor == round(4000.0 / 400.0, 2)
    assert metrics.total_pnl_usd == 3600.0
    assert metrics.average_r_multiple == 1.4
    assert metrics.sharpe_ratio > 1.0
    assert metrics.sortino_ratio > 1.0


def test_slippage_analysis_edge_cases():
    # Empty
    empty_slip = QuantitativeAnalyticsEngine.analyze_slippage_records([])
    assert empty_slip.total_analyzed_trades == 0
    assert empty_slip.execution_quality_score == 100.0

    # Normal mix
    slippages = [0.1, 0.2, -0.1, 0.0, 0.5, -0.2]
    report = QuantitativeAnalyticsEngine.analyze_slippage_records(slippages)
    assert report.total_analyzed_trades == 6
    assert report.max_adverse_slippage_pips == 0.5
    assert report.adverse_execution_rate_pct > 0
    assert 0.0 <= report.execution_quality_score <= 100.0


def test_adaptive_rebalancer_cold_start():
    # < 5 trades
    metrics = RollingPerformanceMetrics(total_trades=3)
    alloc = AdaptiveWeightRebalancer.evaluate_strategy_weight("S1", "OrderFlow Momentum", metrics)
    assert alloc.risk_multiplier == 1.0
    assert alloc.is_throttled is False
    assert "Sample size < 5" in alloc.rebalance_reason


def test_adaptive_rebalancer_degradation_throttling():
    # Severe DD >= 5% -> RETIRED (0.0x)
    severe_metrics = RollingPerformanceMetrics(
        total_trades=20,
        max_drawdown_pct=5.5,
        sortino_ratio=0.4,
        consecutive_losses_max=7,
    )
    alloc = AdaptiveWeightRebalancer.evaluate_strategy_weight("S2", "Breakout", severe_metrics)
    assert alloc.recommended_status == "RETIRED"
    assert alloc.risk_multiplier == 0.0
    assert alloc.is_throttled is True

    # Degraded -> DEGRADED (0.25x)
    degraded_metrics = RollingPerformanceMetrics(
        total_trades=20,
        max_drawdown_pct=3.5,
        sortino_ratio=0.4,
        profit_factor=0.7,
        consecutive_losses_max=4,
    )
    alloc_deg = AdaptiveWeightRebalancer.evaluate_strategy_weight("S3", "MeanReversion", degraded_metrics)
    assert alloc_deg.recommended_status == "DEGRADED"
    assert alloc_deg.risk_multiplier == 0.25
    assert alloc_deg.is_throttled is True


@pytest.mark.asyncio
async def test_analytics_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/analytics/rolling-metrics", headers=AUTH_HEADERS)
        assert res.status_code == 200
        data = res.json()
        assert "win_rate_pct" in data
        assert "sharpe_ratio" in data
        assert "sortino_ratio" in data

        res_slip = await client.get("/api/analytics/slippage-report", headers=AUTH_HEADERS)
        assert res_slip.status_code == 200
        slip_data = res_slip.json()
        assert "execution_quality_score" in slip_data

        res_strat = await client.get("/api/analytics/strategy-weights", headers=AUTH_HEADERS)
        assert res_strat.status_code == 200
        assert isinstance(res_strat.json(), list)
