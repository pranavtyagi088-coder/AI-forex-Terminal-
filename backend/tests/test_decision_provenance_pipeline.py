import pytest
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest
from app.engines.execution.staging import OrderStagingManager, ProposalStatus
from app.engines.decision.snapshot import audit_trail_engine, NoTradeReasonEnum


@pytest.fixture
def gatekeeper():
    return PreFlightGatekeeper()


@pytest.fixture
def staging_mgr(gatekeeper):
    return OrderStagingManager(gatekeeper=gatekeeper)


def test_preflight_generates_cryptographic_audit_receipt(gatekeeper):
    """Every preflight check must issue a decision_id with verified SHA256 integrity."""
    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
    )
    res = gatekeeper.evaluate(req)
    
    assert res.allowed is True
    assert res.decision_id is not None
    assert res.decision_id.startswith("DEC-")
    assert res.integrity_hash is not None
    
    # Cryptographic tamper verification
    assert audit_trail_engine.verify_integrity(res.decision_id) is True
    
    # Retrieve snapshot and check field-level provenance
    snapshot = audit_trail_engine.get_snapshot(res.decision_id)
    assert snapshot is not None
    assert "entry_price" in snapshot.provenance_snapshot
    assert snapshot.provenance_snapshot["entry_price"].source == "BROKER_FEED"


def test_staged_proposal_inherits_decision_audit_id(staging_mgr):
    """Order staging must link to the gatekeeper cryptographic decision snapshot."""
    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
    )
    staged = staging_mgr.stage_order(req, idempotency_key="TEST-DEC-LINK-1")
    
    assert staged.status == ProposalStatus.PENDING_APPROVAL
    assert staged.decision_id is not None
    assert staged.integrity_hash is not None
    assert audit_trail_engine.verify_integrity(staged.decision_id) is True


def test_vetoed_preflight_records_structured_no_trade_reasons(gatekeeper):
    """Vetoed trade must record accurate NoTradeReasonEnum in the immutable snapshot."""
    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0850,  # Invalid SL above entry
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
    )
    res = gatekeeper.evaluate(req)
    assert res.allowed is False
    
    snapshot = audit_trail_engine.get_snapshot(res.decision_id)
    assert snapshot is not None
    assert snapshot.decision_type == "NO_TRADE"
    assert NoTradeReasonEnum.INVALID_SL_GEOMETRY in snapshot.no_trade_reasons
    assert audit_trail_engine.verify_integrity(res.decision_id) is True
