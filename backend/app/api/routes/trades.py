"""API routes for managing live, paper trades, staging proposals, pre-flight risk checks, and Institutional Broker Bridge."""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any

from app.core.auth import verify_api_token
from app.core.database import get_db
from app.models.trade import Trade
from app.models.strategy import Strategy
from app.services.broker.paper import TradeOrderRequest, close_paper_trade, execute_paper_order
from app.services.broker.base import BrokerOrderRequest, PositionInfo, BrokerAccountInfo
from app.services.broker.mt5_adapter import MT5BrokerAdapter
from app.services.broker.bridge import InstitutionalBrokerBridge
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest, PreFlightTradeResponse
from app.engines.execution.staging import OrderStagingManager, StagedProposal, ProposalStatus
from app.engines.analytics.outcome import OutcomeAnalyzer, ExitReasonEnum, TradeOutcome
from app.engines.strategy.decay_detector import DecayDetector, StrategyMetrics
from app.engines.events.bus import event_bus

router = APIRouter(prefix="/api/trades", tags=["trades"])

gatekeeper = PreFlightGatekeeper()
staging_manager = OrderStagingManager(gatekeeper=gatekeeper)
broker_adapter = MT5BrokerAdapter(is_sandbox=True)
broker_bridge = InstitutionalBrokerBridge(adapter=broker_adapter, staging_manager=staging_manager)


class StageOrderPayload(BaseModel):
    request: PreFlightTradeRequest
    idempotency_key: str
    max_slippage_pips: float = 1.0


class ApproveProposalPayload(BaseModel):
    current_market_price: float
    analysis_id: Optional[int] = None
    strategy_id: Optional[int] = None
    execution_mode: str = "LIVE"  # "LIVE" (via BrokerBridge) or "PAPER" (DB only)


class EmergencyClosePayload(BaseModel):
    ticket: Optional[str] = None
    reason: str = "Institutional Risk Intercept"


class OpenTradePayload(BaseModel):
    analysis_id: Optional[int] = None
    strategy_id: Optional[int] = None
    symbol: str
    direction: str
    position_size_lots: float
    entry_price: float
    stop_loss: float
    take_profit: Optional[float] = None
    slippage_pips: float = 0.5


class CloseTradePayload(BaseModel):
    trade_id: int
    exit_price: float
    symbol: Optional[str] = None
    direction: Optional[str] = None
    exit_reason: str = "MANUAL"
    notes: Optional[str] = None


@router.post("/pre-flight-check", response_model=PreFlightTradeResponse)
def run_pre_flight_check(payload: PreFlightTradeRequest) -> PreFlightTradeResponse:
    """Pre-Flight 9-Gate Risk Evaluation."""
    return gatekeeper.evaluate(payload)


@router.post("/proposals/stage", response_model=StagedProposal)
def stage_trade_proposal(payload: StageOrderPayload) -> StagedProposal:
    """Stage an order through the 9-Gate Pre-Flight Gatekeeper."""
    return staging_manager.stage_order(
        req=payload.request,
        idempotency_key=payload.idempotency_key,
        max_slippage_pips=payload.max_slippage_pips,
    )


@router.get("/proposals/{proposal_id}", response_model=StagedProposal)
def get_proposal_status(proposal_id: str) -> StagedProposal:
    """Retrieve staged proposal by ID."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found.")
    return proposal


@router.get("/proposals")
async def list_all_proposals(_token: str = Depends(verify_api_token)):
    """List all staged proposals in memory (pending + processed)."""
    proposals = staging_manager.list_all_proposals() if hasattr(staging_manager, 'list_all_proposals') else []
    return {
        "proposals": [
            {
                "proposal_id": p.proposal_id,
                "status": p.status,
                "symbol": p.request.symbol,
                "direction": p.request.direction,
                "entry_price": float(p.request.entry_price),
                "stop_loss": float(p.request.stop_loss),
                "take_profit": float(p.request.take_profit) if p.request.take_profit else None,
                "position_size_lots": float(p.request.position_size_lots) if hasattr(p.request, 'position_size_lots') else None,
                "gates_passed": p.gates_passed if hasattr(p, 'gates_passed') else 0,
                "created_at": p.created_at.isoformat() if hasattr(p, 'created_at') and p.created_at else None,
            }
            for p in proposals
        ],
        "total": len(proposals),
    }


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str, _token: str = Depends(verify_api_token)):
    """Manually reject a staged proposal (human veto)."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found")
    if hasattr(staging_manager, 'reject_proposal'):
        staging_manager.reject_proposal(proposal_id, reason="MANUAL_HUMAN_VETO")
    else:
        proposal.status = "REJECTED"
    return {
        "proposal_id": proposal_id,
        "status": "REJECTED",
        "reason": "MANUAL_HUMAN_VETO",
    }


@router.post("/proposals/{proposal_id}/approve")
async def approve_and_execute_proposal(
    proposal_id: str,
    payload: ApproveProposalPayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Human approval gate: verify slippage drift and dispatch to Institutional Broker Bridge or Paper DB."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found.")

    if payload.execution_mode.upper() == "LIVE":
        if not broker_adapter._is_connected:
            await broker_adapter.connect()
        receipt = await broker_bridge.execute_proposal(
            proposal_id=proposal_id,
            current_market_price=payload.current_market_price,
        )
        if not receipt.success:
            raise HTTPException(422, f"Broker Bridge Rejection: {receipt.error_message}")
        return {
            "status": "success",
            "proposal_id": proposal_id,
            "execution_mode": "LIVE_BROKER",
            "ticket": receipt.ticket,
            "fill_price": receipt.fill_price,
            "fill_lots": receipt.fill_lots,
            "slippage_pips": receipt.slippage_pips,
            "executed_at": receipt.executed_at.isoformat(),
        }

    # Fallback to Paper DB Order
    approved = staging_manager.approve_and_verify_slippage(
        proposal_id=proposal_id,
        current_market_price=payload.current_market_price,
    )
    if approved.status == ProposalStatus.REJECTED:
        raise HTTPException(422, f"Execution aborted: {approved.rejection_reason}")
    elif approved.status == ProposalStatus.EXPIRED:
        raise HTTPException(410, f"Execution aborted: {approved.rejection_reason}")

    order = TradeOrderRequest(
        analysis_id=payload.analysis_id,
        strategy_id=payload.strategy_id,
        symbol=approved.symbol,
        direction=approved.direction,
        position_size_lots=approved.position_size_lots,
        entry_price=approved.entry_price,
        stop_loss=approved.stop_loss,
        take_profit=approved.take_profit,
        slippage_pips=approved.max_slippage_pips,
    )
    try:
        trade = await execute_paper_order(db, order)
        staging_manager.mark_executed(
            proposal_id=proposal_id,
            fill_price=float(trade.entry_fill),
            ticket=f"PAPER-{trade.id}",
        )
        return {
            "status": "success",
            "proposal_id": proposal_id,
            "execution_mode": "PAPER_DB",
            "trade_id": trade.id,
            "entry_fill": float(trade.entry_fill),
            "position_size_lots": float(trade.position_size_lots),
        }
    except Exception as e:
        raise HTTPException(500, f"Broker execution failure: {str(e)}")


@router.get("/broker/account")
async def get_broker_account_info(_token: str = Depends(verify_api_token)):
    """Get real-time broker account connection status, balance, equity, and latency."""
    if not broker_adapter._is_connected:
        await broker_adapter.connect()
    info = await broker_adapter.get_account_info()
    latency_ms = await broker_adapter.get_heartbeat_latency_ms()
    return {
        "account_id": info.account_id,
        "balance": info.balance,
        "equity": info.equity,
        "free_margin": info.free_margin,
        "currency": info.currency,
        "is_connected": info.is_connected,
        "latency_ms": round(latency_ms, 2),
    }


@router.get("/broker/positions")
async def get_broker_positions(_token: str = Depends(verify_api_token)):
    """Get live open positions directly from broker adapter."""
    if not broker_adapter._is_connected:
        await broker_adapter.connect()
    positions = await broker_adapter.get_open_positions()
    return {"positions": positions, "total_open": len(positions)}


@router.post("/broker/emergency-close")
async def emergency_close_positions(payload: EmergencyClosePayload, _token: str = Depends(verify_api_token)):
    """Fail-Closed Emergency Liquidation: Instant broker order cancellation and position closure."""
    if not broker_adapter._is_connected:
        await broker_adapter.connect()
    if payload.ticket:
        closed = await broker_adapter.close_position(payload.ticket)
        return {"status": "success" if closed else "failed", "closed_ticket": payload.ticket, "reason": payload.reason}
    
    positions = await broker_adapter.get_open_positions()
    closed_tickets = []
    for pos in positions:
        ok = await broker_adapter.close_position(pos.ticket)
        if ok:
            closed_tickets.append(pos.ticket)
    return {"status": "success", "liquidated_tickets": closed_tickets, "count": len(closed_tickets), "reason": payload.reason}


@router.post("/execute")
async def execute_trade(
    req: OpenTradePayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Execute paper order directly."""
    order = TradeOrderRequest(
        analysis_id=req.analysis_id,
        strategy_id=req.strategy_id,
        symbol=req.symbol,
        direction=req.direction,
        position_size_lots=req.position_size_lots,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        slippage_pips=req.slippage_pips,
    )
    trade = await execute_paper_order(db, order)
    return {"status": "success", "trade_id": trade.id, "entry_fill": float(trade.entry_fill)}


@router.post("/close")
async def close_trade(
    req: CloseTradePayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Close an open trade and evaluate strategy outcome."""
    result = await db.execute(select(Trade).where(Trade.id == req.trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    if trade.status == "CLOSED":
        raise HTTPException(status_code=400, detail="Trade is already closed")

    sym = req.symbol or trade.symbol
    dirn = req.direction or trade.direction

    trade = await close_paper_trade(
        db=db,
        trade_id=trade.id,
        exit_price=req.exit_price,
        symbol=sym,
        direction=dirn,
    )
    pnl_usd = float(getattr(trade, "pnl", 0.0) or 0.0)
    return {
        "status": "success",
        "trade_id": trade.id,
        "pnl": pnl_usd,
        "realized_pnl": pnl_usd,
        "realized_pnl_usd": pnl_usd,
        "exit_price": float(getattr(trade, "exit_fill", req.exit_price) or req.exit_price),
    }


@router.get("/open")
async def get_open_trades(
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Get all active open trades."""
    result = await db.execute(select(Trade).where(Trade.status == "OPEN"))
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "position_size_lots": float(t.position_size_lots or 0.0),
            "entry_fill": float(t.entry_fill or 0.0),
            "stop_loss": float(t.stop_loss or 0.0),
            "take_profit": float(t.take_profit) if t.take_profit else None,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
        }
        for t in trades
    ]


@router.get("/history")
async def get_trade_history(
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Get all closed trade history."""
    result = await db.execute(select(Trade).where(Trade.status == "CLOSED"))
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "direction": t.direction,
            "position_size_lots": float(t.position_size_lots or 0.0),
            "entry_fill": float(t.entry_fill or 0.0),
            "exit_fill": float(t.exit_fill) if t.exit_fill else None,
            "pnl": float(t.pnl or 0.0),
            "realized_pnl_usd": float(t.pnl or 0.0),
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]
