import pytest
from app.engines.risk.calculator import (
    MissingRateError, RiskRequest, calculate_pip_value_usd, calculate_position_size
)

def test_pip_value_when_usd_is_quote_currency_needs_no_conversion():
    pip_value = calculate_pip_value_usd(0.0001, 100_000, "USD", {})
    assert pip_value == pytest.approx(10.0)

def test_pip_value_for_usd_jpy_matches_hand_calculation():
    pip_value = calculate_pip_value_usd(0.01, 100_000, "JPY", {"USD/JPY": 150.00})
    assert pip_value == pytest.approx(1000 / 150.00)

def test_usd_jpy_position_size_fix_vs_old_buggy_behavior():
    req = RiskRequest(10_000, 1.0, 150.00, 149.50, 151.00, 30, 0.01, 100_000, "JPY")
    live_rates = {"USD/JPY": 150.00}
    fixed = calculate_position_size(req, live_rates)
    old_buggy_pip_value = req.pip_size * req.contract_size
    old_buggy_lots = round((req.account_balance * req.risk_percent / 100) / (fixed.sl_pips * old_buggy_pip_value), 4)

    assert fixed.pip_value_usd == pytest.approx(6.6667, abs=1e-3)
    assert fixed.position_size_lots > old_buggy_lots * 100
    assert fixed.rr_tp1 == pytest.approx(2.0)
    assert fixed.potential_loss == pytest.approx(100.0, abs=0.5)

def test_cross_pair_gbp_jpy_only_needs_the_quote_currency_rate():
    pip_value = calculate_pip_value_usd(0.01, 100_000, "JPY", {"USD/JPY": 190.00})
    assert pip_value == pytest.approx(1000 / 190.00)

def test_missing_rate_raises_instead_of_guessing():
    with pytest.raises(MissingRateError):
        calculate_pip_value_usd(0.01, 100_000, "JPY", {})

def test_eur_usd_full_calculation_end_to_end():
    req = RiskRequest(10_000, 1.0, 1.1000, 1.0950, 1.1100, 30, 0.0001, 100_000, "USD", take_profit_2=1.1150)
    result = calculate_position_size(req, {})
    assert result.max_risk_amount == pytest.approx(100.0)
    assert result.sl_pips == pytest.approx(50.0)
    assert result.pip_value_usd == pytest.approx(10.0)
    assert result.position_size_lots == pytest.approx(0.2, abs=0.001)
    assert result.rr_tp1 == pytest.approx(2.0)
    assert result.rr_tp2 == pytest.approx(3.0)
    assert result.potential_loss == pytest.approx(100.0, abs=0.5)
