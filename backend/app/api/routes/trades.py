"""API routes for managing live, paper trades, and pre-flight risk checks."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_api_token
from app.core.database import get_db
from app.models.trade import Trade
from app.services.broker.paper import TradeOrderRequest, close_paper_trade, execute_paper_order
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest, PreFlightTradeResponse

router = APIRouter(prefix="/api/trades", tags=["trades"])
gatekeeper = PreFlightGatekeeper()


class OpenTradePayload(BaseModel):
    analysis_id: int | None = None
    symbol: str
    direction: str  # "BUY" | "SELL"
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


@router.post("/pre-flight-check", response_model=PreFlightTradeResponse)
def run_pre_flight_check(payload: PreFlightTradeRequest) -> PreFlightTradeResponse:
    """Evaluate aggregate pre-flight safety gates before order staging."""
    try:
        result = gatekeeper.evaluate(payload)
        return result
    except Exception as e:
        raise HTTPException(400, f"Pre-flight evaluation error: {str(e)}")


@router.post("/execute")
async def execute_trade(
    req: OpenTradePayload,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    """Execute a paper order."""
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
    """Close an open paper trade and calculate realized PnL."""
    try:
        trade = await close_paper_trade(
            db=db,
            trade_id=req.trade_id,
            exit_price=req.exit_price,
            symbol=req.symbol,
            direction=req.direction,
        )
        return {
            "status": "success",
            "trade_id": trade.id,
            "exit_fill": float(trade.exit_fill),
            "realized_pnl_usd": float(trade.pnl),
            "closed_at": trade.closed_at.isoformat() if trade.closed_at else None,
            "trade_status": trade.status,
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
