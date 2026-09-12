import pytest
import asyncio
from app.engines.risk.gatekeeper import PreFlightTradeRequest
from app.engines.execution.staging import ProposalStatus
from app.services.broker.mt5_adapter import MT5BrokerAdapter
from app.services.broker.bridge import InstitutionalBrokerBridge
from app.services.broker.base import BrokerOrderRequest


@pytest.mark.asyncio
async def test_broker_bridge_successful_execution():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()
    bridge = InstitutionalBrokerBridge(adapter=adapter)

    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        take_profit=1.0950,
        account_balance=100000.0,
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=1.2,
    )

    proposal = bridge.staging.stage_order(req, idempotency_key="TEST-KEY-001")
    assert proposal.status == ProposalStatus.PENDING_APPROVAL

    receipt = await bridge.execute_proposal(proposal.proposal_id, current_market_price=1.0850)
    assert receipt.success is True
    assert receipt.ticket is not None
    assert receipt.fill_price > 0.0

    updated_prop = bridge.staging.get_proposal(proposal.proposal_id)
    assert updated_prop.status == ProposalStatus.EXECUTED


@pytest.mark.asyncio
async def test_broker_bridge_spread_veto_no_dispatch():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()
    bridge = InstitutionalBrokerBridge(adapter=adapter)

    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        account_balance=100000.0,
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=5.5,  # Breaches max spread
    )

    proposal = bridge.staging.stage_order(req, idempotency_key="TEST-SPREAD-VETO")
    assert proposal.status == ProposalStatus.REJECTED

    receipt = await bridge.execute_proposal(proposal.proposal_id, current_market_price=1.0850)
    assert receipt.success is False


@pytest.mark.asyncio
async def test_broker_bridge_slippage_drift_rejection():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()
    bridge = InstitutionalBrokerBridge(adapter=adapter)

    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        account_balance=100000.0,
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=1.0,
    )

    proposal = bridge.staging.stage_order(req, idempotency_key="TEST-SLIPPAGE", max_slippage_pips=1.0)
    # Price drifted 5 pips (1.0850 -> 1.0855)
    receipt = await bridge.execute_proposal(proposal.proposal_id, current_market_price=1.0855)
    assert receipt.success is False
    assert "Slippage" in str(receipt.error_message)


@pytest.mark.asyncio
async def test_mt5_adapter_hard_stop_loss_mandatory():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()

    naked_order = BrokerOrderRequest(
        symbol="EURUSD",
        direction="BUY",
        lot_size=1.0,
        entry_price=1.0850,
        stop_loss=0.0,  # Naked order (FORBIDDEN)
    )
    receipt = await adapter.place_order(naked_order)
    assert receipt.success is False
    assert "Stop-Loss" in str(receipt.error_message)


@pytest.mark.asyncio
async def test_broker_disconnect_fail_closed():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    # Disconnected state
    await adapter.disconnect()

    order = BrokerOrderRequest(
        symbol="EURUSD",
        direction="BUY",
        lot_size=1.0,
        entry_price=1.0850,
        stop_loss=1.0800
    )
    receipt = await adapter.place_order(order)
    assert receipt.success is False
    assert "not connected" in str(receipt.error_message)


@pytest.mark.asyncio
async def test_broker_idempotency_protection():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()
    bridge = InstitutionalBrokerBridge(adapter=adapter)

    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        stop_loss=1.0800,
        account_balance=100000.0,
        account_equity=100000.0,
        risk_per_trade_pct=1.0,
        current_spread_pips=1.2,
    )

    p1 = bridge.staging.stage_order(req, idempotency_key="IDEM-001")
    p2 = bridge.staging.stage_order(req, idempotency_key="IDEM-001")
    assert p1.proposal_id == p2.proposal_id


@pytest.mark.asyncio
async def test_mt5_heartbeat_latency():
    adapter = MT5BrokerAdapter(is_sandbox=True)
    await adapter.connect()
    latency = await adapter.get_heartbeat_latency_ms()
    assert latency >0.0 and latency < 500.0
