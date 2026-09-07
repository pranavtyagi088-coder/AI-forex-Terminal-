import pytest
import time
from app.engines.execution.staging import OrderStagingManager, ProposalStatus
from app.engines.risk.gatekeeper import PreFlightTradeRequest


class TestOrderStagingAndIdempotency:
    def test_stage_clean_order_creates_pending_approval(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
        )
        prop = mgr.stage_order(req=req, idempotency_key="unique-key-1")
        assert prop.status == ProposalStatus.PENDING_APPROVAL
        assert prop.position_size_lots > 0
        assert prop.proposal_id.startswith("PROP-")

    def test_idempotent_duplicate_request_returns_same_proposal(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        p1 = mgr.stage_order(req=req, idempotency_key="key-abc-123")
        p2 = mgr.stage_order(req=req, idempotency_key="key-abc-123")
        assert p1.proposal_id == p2.proposal_id
        assert p1.created_at_ts == p2.created_at_ts

    def test_rejection_at_stage_when_risk_breached(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
            circuit_breaker_state="KILL_SWITCH",
        )
        prop = mgr.stage_order(req=req, idempotency_key="key-fail-1")
        assert prop.status == ProposalStatus.REJECTED
        assert "KILL_SWITCH" in prop.rejection_reason

    def test_slippage_guard_rejects_runaway_market(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        prop = mgr.stage_order(req=req, idempotency_key="key-slip-1", max_slippage_pips=1.0)
        
        evaluated = mgr.approve_and_verify_slippage(prop.proposal_id, current_market_price=1.1003)
        assert evaluated.status == ProposalStatus.REJECTED
        assert "Slippage limit breached" in evaluated.rejection_reason

    def test_slippage_guard_approves_within_tolerance(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        prop = mgr.stage_order(req=req, idempotency_key="key-slip-2", max_slippage_pips=1.5)
        
        evaluated = mgr.approve_and_verify_slippage(prop.proposal_id, current_market_price=1.10005)
        assert evaluated.status == ProposalStatus.APPROVED

    def test_expired_proposal_cannot_be_approved(self):
        mgr = OrderStagingManager(ttl_seconds=0.01)
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        prop = mgr.stage_order(req=req, idempotency_key="key-exp-1")
        time.sleep(0.02)
        evaluated = mgr.approve_and_verify_slippage(prop.proposal_id, current_market_price=1.1000)
        assert evaluated.status == ProposalStatus.EXPIRED

    def test_mark_executed_lifecycle(self):
        mgr = OrderStagingManager()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        prop = mgr.stage_order(req=req, idempotency_key="key-exec-1")
        approved = mgr.approve_and_verify_slippage(prop.proposal_id, current_market_price=1.1000)
        assert approved.status == ProposalStatus.APPROVED
        
        executed = mgr.mark_executed(approved.proposal_id, fill_price=1.10002, ticket="TICKET-999")
        assert executed.status == ProposalStatus.EXECUTED
        assert executed.execution_ticket == "TICKET-999"
