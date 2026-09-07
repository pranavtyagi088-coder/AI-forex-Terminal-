import pytest
from app.engines.risk.calculator import (
    MissingRateError,
    RiskRequest,
    calculate_pip_value_usd,
    calculate_position_size,
    clamp_and_step_lots,
    normalize_rate_key
)


class TestPipValueCalculations:
    """Deterministic test vectors for pip values across major, cross, and metal pairs."""

    def test_usd_quote_pair_eurusd(self):
        val = calculate_pip_value_usd(0.0001, 100_000, "USD", {})
        assert val == pytest.approx(10.0)

    def test_usd_base_pair_usdjpy(self):
        val = calculate_pip_value_usd(0.01, 100_000, "JPY", {"USDJPY": 150.00})
        assert val == pytest.approx(1000.0 / 150.00, rel=1e-4)

    def test_cross_pair_eurgbp_multiplies_gbpusd(self):
        val = calculate_pip_value_usd(0.0001, 100_000, "GBP", {"GBPUSD": 1.2800})
        assert val == pytest.approx(12.80, rel=1e-4)

    def test_cross_pair_gbpjpy_divides_usdjpy(self):
        val = calculate_pip_value_usd(0.01, 100_000, "JPY", {"USD/JPY": 190.00})
        assert val == pytest.approx(1000.0 / 190.00, rel=1e-4)

    def test_gold_xauusd(self):
        val = calculate_pip_value_usd(0.01, 100, "USD", {})
        assert val == pytest.approx(1.00)

    def test_missing_rate_fail_closed(self):
        with pytest.raises(MissingRateError):
            calculate_pip_value_usd(0.01, 100_000, "CHF", {})


class TestLotSteppingAndClamping:
    """Test deterministic lot sizing stepping and safety limits."""

    def test_step_down_safety(self):
        stepped = clamp_and_step_lots(0.237, lot_step=0.01, min_lot=0.01, max_lot=100.0)
        assert stepped == 0.23

    def test_min_lot_clamp(self):
        stepped = clamp_and_step_lots(0.005, lot_step=0.01, min_lot=0.01, max_lot=100.0)
        assert stepped == 0.01

    def test_max_lot_clamp(self):
        stepped = clamp_and_step_lots(150.0, lot_step=0.01, min_lot=0.01, max_lot=100.0)
        assert stepped == 100.0


class TestDeterministicPositionSizingVectors:
    """Deterministic end-to-end position sizing vectors."""

    def test_eurusd_standard_risk_vector(self):
        req = RiskRequest(
            account_balance=10000.0,
            risk_percent=1.0,
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit_1=1.1100,
            take_profit_2=1.1150,
            pip_size=0.0001,
            contract_size=100000.0,
            quote_currency="USD"
        )
        res = calculate_position_size(req)
        assert res.allowed is True
        assert res.max_risk_amount == 100.0
        assert res.sl_pips == 50.0
        assert res.pip_value_usd == 10.0
        assert res.position_size_lots == 0.20
        assert res.position_size_units == 20000.0
        assert res.rr_tp1 == 2.0
        assert res.rr_tp2 == 3.0
        assert res.potential_loss == 100.0
        assert res.potential_profit_usd == 200.0

    def test_usdjpy_risk_vector(self):
        req = RiskRequest(
            account_balance=50000.0,
            risk_percent=0.5,
            entry_price=155.00,
            stop_loss=154.50,
            take_profit_1=156.00,
            pip_size=0.01,
            contract_size=100000.0,
            quote_currency="JPY"
        )
        res = calculate_position_size(req, {"USDJPY": 155.00})
        assert res.max_risk_amount == 250.0
        assert res.sl_pips == 50.0
        assert res.position_size_lots == 0.77
        assert res.rr_tp1 == 2.0
        assert res.potential_loss <= 250.0

    def test_eurgbp_risk_vector(self):
        req = RiskRequest(
            account_balance=20000.0,
            risk_percent=1.0,
            entry_price=0.8500,
            stop_loss=0.8460,
            take_profit_1=0.8580,
            pip_size=0.0001,
            contract_size=100000.0,
            quote_currency="GBP"
        )
        res = calculate_position_size(req, {"GBPUSD": 1.2500})
        assert res.max_risk_amount == 200.0
        assert res.sl_pips == 40.0
        assert res.pip_value_usd == 12.50
        assert res.position_size_lots == 0.40
        assert res.rr_tp1 == 2.0
        assert res.potential_loss == 200.0
