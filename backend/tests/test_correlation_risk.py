import pytest
from app.engines.risk.correlation import (
    CorrelationRiskEngine,
    OpenPositionInput,
    AggregateRiskLimits,
    decompose_pair
)


class TestPairDecomposition:
    """Test standard currency decomposition for long/short exposure."""

    def test_buy_eurusd_decomposition(self):
        base, quote, long_c, short_c = decompose_pair("EUR/USD", "BUY")
        assert base == "EUR"
        assert quote == "USD"
        assert long_c == "EUR"
        assert short_c == "USD"

    def test_sell_usdjpy_decomposition(self):
        base, quote, long_c, short_c = decompose_pair("USDJPY", "SELL")
        assert base == "USD"
        assert quote == "JPY"
        assert long_c == "JPY"
        assert short_c == "USD"


class TestAggregateRiskEvaluation:
    """Deterministic test vectors for aggregate risk & correlation clustering."""

    def test_single_trade_allowed_within_limits(self):
        engine = CorrelationRiskEngine()
        result = engine.evaluate_aggregate_risk(
            account_balance=100000.0,
            open_positions=[],
            proposed_symbol="EUR/USD",
            proposed_direction="BUY",
            proposed_risk_usd=1000.0,
            proposed_risk_pct=1.0,
        )
        assert result.allowed is True
        assert result.projected_total_risk_pct == 1.0
        assert result.currency_exposures_pct["USD"] == 1.0
        assert result.currency_exposures_pct["EUR"] == 1.0
        assert len(result.violations) == 0

    def test_currency_cluster_overexposure_blocked(self):
        """
        If we have BUY EURUSD (1% risk) and BUY GBPUSD (1.5% risk),
        and we try to add BUY AUDUSD (1% risk), total USD exposure = 3.5% (> 3.0% limit).
        This must be blocked!
        """
        engine = CorrelationRiskEngine(limits=AggregateRiskLimits(max_currency_cluster_risk_pct=3.0))
        open_trades = [
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_amount_usd=1000.0, risk_pct=1.0),
            OpenPositionInput(symbol="GBPUSD", direction="BUY", risk_amount_usd=1500.0, risk_pct=1.5),
        ]
        result = engine.evaluate_aggregate_risk(
            account_balance=100000.0,
            open_positions=open_trades,
            proposed_symbol="AUDUSD",
            proposed_direction="BUY",
            proposed_risk_usd=1000.0,
            proposed_risk_pct=1.0, # 1.0 + 1.5 + 1.0 = 3.5% on USD
        )
        assert result.allowed is False
        assert any("EXCEEDS_CURRENCY_CLUSTER_LIMIT" in v for v in result.violations)
        assert result.currency_exposures_pct["USD"] == 3.5

    def test_total_portfolio_risk_cap_blocked(self):
        """
        Portfolio cap = 5.0%. Open risk = 4.5%. Proposed = 1.0%. Total = 5.5%. Must be blocked!
        """
        engine = CorrelationRiskEngine(limits=AggregateRiskLimits(max_portfolio_risk_pct=5.0))
        open_trades = [
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_amount_usd=2500.0, risk_pct=2.5),
            OpenPositionInput(symbol="USDJPY", direction="BUY", risk_amount_usd=2000.0, risk_pct=2.0),
        ]
        result = engine.evaluate_aggregate_risk(
            account_balance=100000.0,
            open_positions=open_trades,
            proposed_symbol="GBPJPY",
            proposed_direction="BUY",
            proposed_risk_usd=1000.0,
            proposed_risk_pct=1.0,
        )
        assert result.allowed is False
        assert any("EXCEEDS_MAX_PORTFOLIO_RISK" in v for v in result.violations)

    def test_high_positive_correlation_triggers_warning(self):
        """
        BUY EURUSD open, proposing BUY GBPUSD (correlation +0.82 >= 0.75 threshold).
        Should generate correlation warning.
        """
        engine = CorrelationRiskEngine()
        open_trades = [
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_amount_usd=1000.0, risk_pct=1.0)
        ]
        result = engine.evaluate_aggregate_risk(
            account_balance=100000.0,
            open_positions=open_trades,
            proposed_symbol="GBPUSD",
            proposed_direction="BUY",
            proposed_risk_usd=1000.0,
            proposed_risk_pct=1.0,
        )
        assert result.allowed is True
        assert len(result.warnings) > 0
        assert any("High positive correlation" in w for w in result.warnings)
