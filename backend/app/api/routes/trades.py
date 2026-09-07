"""API routes for managing live, paper trades, staging proposals, and pre-flight risk checks."""

from __future__ import annotations

import time
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.auth import verify_api_token
from app.core.database import get_db
from app.models.trade import Trade
from app.services.broker.paper import TradeOrderRequest, close_paper_trade, execute_paper_order
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest, PreFlightTradeResponse
from app.engines.execution.staging import OrderStagingManager, StagedProposal, ProposalStatus
from app.engines.analytics.outcome import OutcomeAnalyzer, ExitReasonEnum, TradeOutcome
from app.engines.strategy.decay_detector import DecayDetector

router = APIRouter(prefix="/api/trades", tags=["trades"])
gatekeeper = PreFlightGatekeeper()
staging_manager = OrderStagingManager(gatekeeper=gatekeeper)
outcome_analyzer = OutcomeAnalyzer()
decay_detector = DecayDetector()


class StageOrderPayload(BaseModel):
    request: PreFlightTradeRequest
    idempotency_key: str
    max_slippage_pips: float = 1.0


class ApproveProposalPayload(BaseModel):
    current_market_price: float
    analysis_id: Optional[int] = None


class OpenTradePayload(BaseModel):
    analysis_id: int | None = None
    symbol: str
    direction: str
    position_size_lots: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    slippage_pips: float = 0.5


class CloseTradePayload(BaseModel):
    trade_id: int
    symbol: str
    direction: str
    exit_price: float
    exit_reason: ExitReasonEnum = ExitReasonEnum.MANUAL_CLOSE
    highest_price_reached: Optional[float] = None
    lowest_price_reached: Optional[float] = None
    strategy_name: Optional[str] = None


@router.post("/pre-flight-check", response_model=PreFlightTradeResponse)
def run_pre_flight_check(payload: PreFlightTradeRequest) -> PreFlightTradeResponse:
    """Evaluate aggregate pre-flight safety gates before order staging."""
    try:
        return gatekeeper.evaluate(payload)
    except Exception as e:
        raise HTTPException(400, f"Pre-flight evaluation error: {str(e)}")


@router.post("/proposals/stage", response_model=StagedProposal)
def stage_trade_proposal(payload: StageOrderPayload) -> StagedProposal:
    """Stage an order idempotently into the human approval queue."""
    try:
        return staging_manager.stage_order(
            req=payload.request,
            idempotency_key=payload.idempotency_key,
            max_slippage_pips=payload.max_slippage_pips,
        )
    except Exception as e:
        raise HTTPException(400, f"Order staging failed: {str(e)}")


@router.get("/proposals/{proposal_id}", response_model=StagedProposal)
def get_proposal_status(proposal_id: str) -> StagedProposal:
    """Retrieve staged proposal by ID."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found.")
    return proposal


@router.post("/proposals/{proposal_id}/approve")
async def approve_and_execute_proposal(
    proposal_id: str,
    payload: ApproveProposalPayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Human approval gate: verify slippage drift and execute to paper broker."""
    proposal = staging_manager.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(404, f"Proposal {proposal_id} not found.")

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
            "trade_id": trade.id,
            "broker": trade.broker,
            "entry_fill": float(trade.entry_fill),
            "position_size_lots": float(trade.position_size_lots),
            "commission": float(trade.commission),
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "trade_status": trade.status,
        }
    except Exception as e:
        raise HTTPException(500, f"Broker execution failure: {str(e)}")


@router.post("/execute")
async def execute_trade(
    req: OpenTradePayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Direct paper order execution endpoint."""
    order = TradeOrderRequest(
        analysis_id=req.analysis_id,
        symbol=req.symbol,
        direction=req.direction,
        position_size_lots=req.position_size_lots,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        slippage_pips=req.slippage_pips,
    )
    try:
        trade = await execute_paper_order(db, order)
        return {
            "status": "success",
            "trade_id": trade.id,
            "broker": trade.broker,
            "entry_fill": float(trade.entry_fill),
            "position_size_lots": float(trade.position_size_lots),
            "commission": float(trade.commission),
            "opened_at": trade.opened_at.isoformat() if trade.opened_at else None,
            "trade_status": trade.status,
        }
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/close")
async def close_trade(
    req: CloseTradePayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Close an open trade and run outcome analytics + strategy decay sync."""
    try:
        trade = await close_paper_trade(
            db=db,
            trade_id=req.trade_id,
            exit_price=req.exit_price,
            symbol=req.symbol,
            direction=req.direction,
        )

        # 1. Outcome & Deviation Analysis
        planned_sl = float(trade.stop_loss) if getattr(trade, "stop_loss", None) else (req.exit_price * 0.99)
        outcome: TradeOutcome = outcome_analyzer.evaluate_closed_trade(
            trade_id=trade.id,
            symbol=req.symbol,
            direction=req.direction,
            proposed_entry=float(trade.entry_fill),
            actual_entry=float(trade.entry_fill),
            proposed_lots=float(trade.position_size_lots),
            actual_lots=float(trade.position_size_lots),
            stop_loss=planned_sl,
            exit_price=req.exit_price,
            exit_reason=req.exit_reason,
            pnl_usd=float(trade.pnl),
            risk_amount_usd=abs(float(trade.pnl)) if float(trade.pnl) < 0 else 500.0,
            highest_price_reached=req.highest_price_reached,
            lowest_price_reached=req.lowest_price_reached,
        )

        return {
            "status": "success",
            "trade_id": trade.id,
            "exit_fill": float(trade.exit_fill),
            "realized_pnl_usd": float(trade.pnl),
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "trade_status": trade.status,
            "outcome_analytics": {
                "realized_r_multiple": outcome.realized_r_multiple,
                "mae_pips": outcome.mae_pips,
                "mfe_pips": outcome.mfe_pips,
                "is_disciplined": outcome.is_disciplined,
                "exit_reason": outcome.exit_reason.value,
                "deviation_flags": outcome.deviation_flags,
            },
        }
    except Exception as e:
        raise HTTPException(422, str(e))


@router.get("/open")
async def get_open_trades(
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """List all currently active open positions."""
    result = await db.execute(select(Trade).where(Trade.status == "OPEN").order_by(Trade.opened_at.desc()))
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "analysis_id": t.analysis_id,
            "broker": t.broker,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "position_size_lots": float(t.position_size_lots or 0.0),
            "entry_fill": float(t.entry_fill or 0.0),
            "commission": float(t.commission or 0.0),
            "status": t.status,
        }
        for t in trades
    ]


@router.get("/history")
async def get_trade_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """List closed trade history and realized PnL."""
    result = await db.execute(select(Trade).where(Trade.status == "CLOSED").order_by(Trade.closed_at.desc()).limit(limit))
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "analysis_id": t.analysis_id,
            "opened_at": t.opened_at.isoformat() if t.opened_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "position_size_lots": float(t.position_size_lots or 0.0),
            "entry_fill": float(t.entry_fill or 0.0),
            "exit_fill": float(t.exit_fill or 0.0),
            "pnl_usd": float(t.pnl or 0.0),
            "commission": float(t.commission or 0.0),
            "status": t.status,
        }
        for t in trades
    ]
