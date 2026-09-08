import pytest
import math
from unittest.mock import MagicMock
from pydantic import ValidationError

from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest
from app.engines.decision.snapshot import DecisionAuditTrailEngine, NoTradeReasonEnum
from app.engines.events.bus import event_bus, EventType, EventSeverity


@pytest.fixture
def gatekeeper():
    return PreFlightGatekeeper()


def test_schema_level_nan_rejection_fail_closed():
    """Pydantic v2 schema rejects NaN for constrained entry fields (Fail-closed by schema)."""
    with pytest.raises(ValidationError):
        PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=float("nan"),
            stop_loss=1.0750,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
        )


def test_fail_closed_on_nan_in_optional_unconstrained_metrics(gatekeeper):
    """NaN float in optional metrics (e.g. spread) triggers gatekeeper numerical sanitization veto."""
    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=float("nan"),  # NaN injected via spread feed
    )
    res = gatekeeper.evaluate(req)
    assert res.allowed is False
    assert res.approved_lot_size == 0.0
    assert any("DATA_FEED_UNCERTAINTY" in r for r in res.rejection_reasons)
    assert res.account_data_status == "UNAVAILABLE"


def test_fail_closed_on_unhandled_engine_exception(gatekeeper):
    """If an internal engine raises an unexpected exception, gatekeeper must NOT crash and must return allowed=False."""
    # Sabotage correlation engine to raise an unhandled runtime error
    gatekeeper.correlation_engine.evaluate_aggregate_risk = MagicMock(
        side_effect=RuntimeError("Simulated catastrophic correlation failure")
    )

    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
    )
    
    res = gatekeeper.evaluate(req)
    
    # Must fail closed deterministically
    assert res.allowed is False
    assert res.approved_lot_size == 0.0
    assert any("SYSTEM_ERROR_FAIL_CLOSED" in r for r in res.rejection_reasons)
    assert res.account_data_status == "UNAVAILABLE"

    # Verify CRITICAL alert was emitted to EventBus
    events = event_bus.get_recent_events(limit=5, severity=EventSeverity.CRITICAL)
    assert len(events) > 0
    assert any("Simulated catastrophic correlation failure" in e.message for e in events)


def test_fail_closed_on_zero_or_negative_currency_quote(gatekeeper):
    """Invalid quote rate causing calculation errors must fail closed."""
    req = PreFlightTradeRequest(
        symbol="USDCHF",
        direction="BUY",
        entry_price=0.9000,
        stop_loss=0.8950,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
        quotes={"USDCHF": -0.5},  # Malformed negative rate from broker
    )
    res = gatekeeper.evaluate(req)
    assert res.allowed is False
    assert any("SYSTEM_ERROR_FAIL_CLOSED" in r for r in res.rejection_reasons)


def test_decision_snapshot_fail_closed_taxonomy():
    """Decision snapshot correctly records fail-closed reason taxonomy with SHA256 integrity."""
    audit_engine = DecisionAuditTrailEngine()
    snap = audit_engine.record_decision(
        symbol="EURUSD",
        direction="BUY",
        decision_type="NO_TRADE",
        no_trade_reasons=[
            NoTradeReasonEnum.SYSTEM_ERROR_FAIL_CLOSED,
            NoTradeReasonEnum.DATA_FEED_UNCERTAINTY,
        ],
    )
    assert snap.decision_type == "NO_TRADE"
    assert NoTradeReasonEnum.SYSTEM_ERROR_FAIL_CLOSED in snap.no_trade_reasons
    assert audit_engine.verify_integrity(snap.decision_id) is True
