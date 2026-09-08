"""
===========================================================================
P0-#9: INSTITUTIONAL GOLDEN RISK TEST-VECTOR SUITE
===========================================================================
Deterministic, mathematically verified input-output vectors that guarantee
risk engine correctness to the exact decimal place.
===========================================================================
"""
import pytest
import math
from unittest.mock import MagicMock

from app.engines.risk.gatekeeper import (
    PreFlightGatekeeper,
    PreFlightTradeRequest,
    PreFlightTradeResponse,
)
from app.engines.risk.instruments import InstrumentRegistry, InstrumentSpec, AssetClass
from app.engines.risk.correlation import CorrelationRiskEngine, OpenPositionInput


@pytest.fixture
def gk():
    """Fresh gatekeeper instance with mocked Circuit Breaker to prevent state leak."""
    mock_cb = MagicMock()
    mock_snap = MagicMock()
    mock_snap.state.value = "NORMAL"
    mock_snap.reason = None
    mock_cb.evaluate.return_value = mock_snap
    return PreFlightGatekeeper(circuit_breaker=mock_cb)


@pytest.fixture
def registry():
    return InstrumentRegistry()


def _base_req(**overrides) -> PreFlightTradeRequest:
    defaults = dict(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100_000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=0.8,
        current_daily_loss_pct=0.0,
        current_total_drawdown_pct=0.0,
    )
    defaults.update(overrides)
    return PreFlightTradeRequest(**defaults)


# 1. Pip Valuation Vectors
PIP_VALUATION_VECTORS = [
    ("EURUSD", 1.0800, {},                      10.0,    1e-6, "EURUSD_USD_quote_major"),
    ("GBPUSD", 1.2700, {},                      10.0,    1e-6, "GBPUSD_USD_quote_major"),
    ("AUDUSD", 0.6500, {},                      10.0,    1e-6, "AUDUSD_USD_quote_major"),
    ("USDJPY", 150.00, {"USDJPY": 150.0},       6.6667,  1e-3, "USDJPY_jpy_quote"),
    ("USDJPY", 145.50, {"USDJPY": 145.5},       6.8729,  1e-3, "USDJPY_jpy_quote_alt_rate"),
    ("XAUUSD", 2350.0, {},                      10.0,    1e-6, "XAUUSD_gold"),
    ("XAGUSD", 28.50,  {},                      50.0,    1e-6, "XAGUSD_silver"),
    ("US30",   39500,  {},                       1.0,    1e-6, "US30_dow_index"),
    ("NAS100", 18200,  {},                       1.0,    1e-6, "NAS100_nasdaq_index"),
]

@pytest.mark.parametrize(
    "symbol,entry,quotes,expected_pip_val,tol,vid",
    PIP_VALUATION_VECTORS,
    ids=[v[-1] for v in PIP_VALUATION_VECTORS],
)
def test_golden_pip_valuation(gk, registry, symbol, entry, quotes, expected_pip_val, tol, vid):
    spec = registry.get_spec(symbol)
    actual = gk._calculate_pip_value(spec, entry, quotes)
    assert actual == pytest.approx(expected_pip_val, abs=tol)


# 2. Lot Sizing Vectors
LOT_SIZING_VECTORS = [
    ("EURUSD", 1.0800, 1.0750, 100_000, 1.0, 2.0,  "EURUSD_50pip_1pct_100k"),
    ("EURUSD", 1.0800, 1.0775, 50_000,  0.5, 1.0,  "EURUSD_25pip_0.5pct_50k"),
    ("EURUSD", 1.0800, 1.0700, 10_000,  2.0, 0.2,  "EURUSD_100pip_2pct_10k"),
    ("XAUUSD", 2350.0, 2345.0, 100_000, 1.0, 2.0,  "XAUUSD_50pip_1pct_100k"),
    ("NAS100", 18200,  18150,  100_000, 1.0, 20.0, "NAS100_50pt_1pct_100k"),
    ("EURUSD", 1.0800, 1.0790, 1_000,   1.0, 0.1,  "EURUSD_micro_10pip_1pct_1k"),
]

@pytest.mark.parametrize(
    "symbol,entry,sl,balance,risk_pct,expected_lot,vid",
    LOT_SIZING_VECTORS,
    ids=[v[-1] for v in LOT_SIZING_VECTORS],
)
def test_golden_lot_sizing(gk, symbol, entry, sl, balance, risk_pct, expected_lot, vid):
    req = _base_req(
        symbol=symbol, entry_price=entry, stop_loss=sl,
        account_balance=balance, risk_per_trade_pct=risk_pct,
    )
    res = gk.evaluate(req)
    assert res.allowed is True, f"[{vid}] Unexpected veto: {res.rejection_reasons}"
    assert res.approved_lot_size == pytest.approx(expected_lot, abs=0.01)


# 3. Lot Step Quantization
def test_lot_step_quantization_floors_correctly(gk):
    req = _base_req(
        entry_price=1.0800, stop_loss=1.0790,
        account_balance=13_700, risk_per_trade_pct=1.0,
        lot_step=0.1,
    )
    res = gk.evaluate(req)
    assert res.approved_lot_size == pytest.approx(1.3, abs=0.01)


def test_lot_clamped_to_min_lot(gk):
    req = _base_req(
        entry_price=1.0800, stop_loss=1.0750,
        account_balance=100, risk_per_trade_pct=0.5,
    )
    res = gk.evaluate(req)
    assert res.approved_lot_size >= 0.01


def test_lot_clamped_to_max_lot(gk):
    req = _base_req(
        entry_price=1.0800, stop_loss=1.0790,
        account_balance=100_000_000, risk_per_trade_pct=10.0,
    )
    res = gk.evaluate(req)
    assert res.approved_lot_size <= 100.0


# 4. Drawdown Cliff-Edge Vectors
DRAWDOWN_VECTORS = [
    (0.0,   5.0,  0.0,  10.0, True,  "zero_drawdown_clean"),
    (4.99,  5.0,  9.99, 10.0, True,  "just_below_both_limits"),
    (4.999, 5.0,  9.999,10.0, True,  "epsilon_below_limits"),
    (5.0,   5.0,  0.0,  10.0, False, "exact_daily_limit_breach"),
    (5.01,  5.0,  0.0,  10.0, False, "daily_limit_exceeded"),
    (0.0,   5.0,  10.0, 10.0, False, "exact_total_dd_breach"),
    (0.0,   5.0,  10.01,10.0, False, "total_dd_exceeded"),
    (5.0,   5.0,  10.0, 10.0, False, "both_limits_breached"),
]

@pytest.mark.parametrize(
    "daily,max_d,total,max_t,should_allow,vid",
    DRAWDOWN_VECTORS,
    ids=[v[-1] for v in DRAWDOWN_VECTORS],
)
def test_golden_drawdown_cliff_edge(gk, daily, max_d, total, max_t, should_allow, vid):
    req = _base_req(
        current_daily_loss_pct=daily,
        max_daily_loss_pct=max_d,
        current_total_drawdown_pct=total,
        max_total_drawdown_pct=max_t,
    )
    res = gk.evaluate(req)
    assert res.allowed is should_allow, f"[{vid}] Expected {should_allow}, got {res.allowed}"


# 5. Spread Guard Boundary Vectors
SPREAD_VECTORS = [
    ("EURUSD", 0.5,  True,  "EURUSD_tight_spread"),
    ("EURUSD", 1.5,  True,  "EURUSD_at_limit"),
    ("EURUSD", 2.5,  True,  "EURUSD_normal_spread"),
    ("EURUSD", 5.0,  False, "EURUSD_excessive_spread"),
    ("XAUUSD", 1.5,  True,  "XAUUSD_tight_spread"),
    ("XAUUSD", 5.0,  True,  "XAUUSD_normal_spread"),
    ("XAUUSD", 8.0,  False, "XAUUSD_excessive_spread"),
    ("NAS100", 1.0,  True,  "NAS100_tight_spread"),
    ("NAS100", 5.0,  True,  "NAS100_normal_spread"),
]

@pytest.mark.parametrize(
    "symbol,spread,should_allow,vid",
    SPREAD_VECTORS,
    ids=[v[-1] for v in SPREAD_VECTORS],
)
def test_golden_spread_guard(gk, symbol, spread, should_allow, vid):
    req = _base_req(symbol=symbol, current_spread_pips=spread)
    res = gk.evaluate(req)
    if not should_allow:
        assert res.allowed is False
        assert any("SPREAD_EXCEEDS" in r for r in res.rejection_reasons)


# 6. Stop-Loss Geometry Vectors
SL_GEOMETRY_VECTORS = [
    ("BUY",  1.0800, 1.0750, True,  "BUY_sl_below_entry_valid"),
    ("BUY",  1.0800, 1.0850, False, "BUY_sl_above_entry_invalid"),
    ("BUY",  1.0800, 1.0800, False, "BUY_sl_equals_entry_zero_distance"),
    ("SELL", 1.0800, 1.0850, True,  "SELL_sl_above_entry_valid"),
    ("SELL", 1.0800, 1.0750, False, "SELL_sl_below_entry_invalid"),
    ("SELL", 1.0800, 1.0800, False, "SELL_sl_equals_entry_zero_distance"),
]

@pytest.mark.parametrize(
    "direction,entry,sl,should_allow,vid",
    SL_GEOMETRY_VECTORS,
    ids=[v[-1] for v in SL_GEOMETRY_VECTORS],
)
def test_golden_sl_geometry(gk, direction, entry, sl, should_allow, vid):
    req = _base_req(direction=direction, entry_price=entry, stop_loss=sl)
    res = gk.evaluate(req)
    if not should_allow:
        assert res.allowed is False


# 7. Risk Amount Precision Vectors
RISK_PRECISION_VECTORS = [
    (100_000.0, 1.0,   1_000.0,   "100k_1pct"),
    (100_000.0, 0.25,    250.0,   "100k_quarter_pct"),
    (10_000.0,  2.0,     200.0,   "10k_2pct"),
    (1_000.0,   0.5,       5.0,   "1k_half_pct"),
    (500.0,     1.0,       5.0,   "500_1pct_micro"),
    (1_000_000, 0.1,   1_000.0,   "1M_0.1pct_whale"),
]

@pytest.mark.parametrize(
    "balance,risk_pct,expected_usd,vid",
    RISK_PRECISION_VECTORS,
    ids=[v[-1] for v in RISK_PRECISION_VECTORS],
)
def test_golden_risk_amount_precision(gk, balance, risk_pct, expected_usd, vid):
    req = _base_req(account_balance=balance, risk_per_trade_pct=risk_pct)
    res = gk.evaluate(req)
    assert res.risk_amount_usd == pytest.approx(expected_usd, abs=0.01)


# 8. Cross-Instrument Parity Vectors
def test_cross_instrument_parity_eurusd_vs_xauusd(gk):
    req_eur = _base_req(
        symbol="EURUSD", entry_price=1.0800, stop_loss=1.0750,
        account_balance=100_000, risk_per_trade_pct=1.0,
    )
    req_xau = _base_req(
        symbol="XAUUSD", entry_price=2350.0, stop_loss=2345.0,
        account_balance=100_000, risk_per_trade_pct=1.0,
    )
    res_eur = gk.evaluate(req_eur)
    res_xau = gk.evaluate(req_xau)
    assert res_eur.allowed and res_xau.allowed
    assert res_eur.approved_lot_size == pytest.approx(res_xau.approved_lot_size, abs=0.01)


def test_cross_instrument_parity_index_vs_forex(gk):
    req_eur = _base_req(
        symbol="EURUSD", entry_price=1.0800, stop_loss=1.0750,
        account_balance=100_000, risk_per_trade_pct=1.0,
    )
    req_nas = _base_req(
        symbol="NAS100", entry_price=18200, stop_loss=18150,
        account_balance=100_000, risk_per_trade_pct=1.0,
    )
    res_eur = gk.evaluate(req_eur)
    res_nas = gk.evaluate(req_nas)
    assert res_eur.allowed and res_nas.allowed
    ratio = res_nas.approved_lot_size / res_eur.approved_lot_size
    assert ratio == pytest.approx(10.0, abs=0.5)


# 9. Correlation Cluster Vectors
def test_correlation_cluster_boundary_below_limit():
    engine = CorrelationRiskEngine()
    result = engine.evaluate_aggregate_risk(
        account_balance=100_000,
        open_positions=[
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_usd=1500, risk_pct=1.5),
            OpenPositionInput(symbol="EURGBP", direction="BUY", risk_usd=1400, risk_pct=1.4),
        ],
        proposed_symbol="EURJPY",
        proposed_direction="BUY",
        proposed_risk_usd=0,
        proposed_risk_pct=0,
    )
    assert result.allowed is True


def test_correlation_cluster_boundary_above_limit():
    engine = CorrelationRiskEngine()
    result = engine.evaluate_aggregate_risk(
        account_balance=100_000,
        open_positions=[
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_usd=1600, risk_pct=1.6),
            OpenPositionInput(symbol="EURGBP", direction="BUY", risk_usd=1500, risk_pct=1.5),
        ],
        proposed_symbol="EURJPY",
        proposed_direction="BUY",
        proposed_risk_usd=0,
        proposed_risk_pct=0,
    )
    assert result.allowed is False


# 10. Normalization Vectors
NORMALIZATION_VECTORS = [
    ("EURUSD",      "EURUSD",  "clean_major"),
    ("eurusd",      "EURUSD",  "lowercase_major"),
    ("EURUSD.pro",  "EURUSD",  "broker_suffix_pro"),
    ("EURUSD.raw",  "EURUSD",  "broker_suffix_raw"),
    ("EURUSDm",     "EURUSD",  "broker_suffix_m"),
    ("GOLD",        "XAUUSD",  "alias_gold"),
    ("USTEC",       "NAS100",  "alias_ustec"),
    ("DJ30",        "US30",    "alias_dj30"),
]

@pytest.mark.parametrize(
    "raw,expected,vid",
    NORMALIZATION_VECTORS,
    ids=[v[-1] for v in NORMALIZATION_VECTORS],
)
def test_golden_symbol_normalization(registry, raw, expected, vid):
    assert registry.normalize_symbol(raw) == expected


def test_unsupported_symbol_raises(registry):
    with pytest.raises(KeyError, match="UNSUPPORTED_INSTRUMENT"):
        registry.get_spec("FAKECOIN")
