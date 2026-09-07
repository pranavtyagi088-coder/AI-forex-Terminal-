from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.config import settings
from app.models.trade import Trade
from app.models.analysis import Analysis

router = APIRouter(prefix="/api/journal", tags=["Trade Journal"])


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization Header"
        )
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization Header Format"
        )
    token = parts[1]
    if token != settings.API_AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or Expired Token"
        )
    return token


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


class TradeCreate(BaseModel):
    symbol: str = "EUR/USD"
    timeframe: str = "1h"
    strategy_name: Optional[str] = None
    direction: str = "BUY"
    position_size_lots: float = 0.1
    entry_fill: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_amount: Optional[float] = None
    rr_planned: Optional[float] = None
    market_regime: Optional[str] = None
    structure_context: Optional[dict] = None
    liquidity_context: Optional[dict] = None
    confidence: Optional[float] = None
    notes: Optional[str] = None


class TradeUpdate(BaseModel):
    exit_fill: Optional[float] = None
    pnl: Optional[float] = None
    realized_r: Optional[float] = None
    result: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TradeResponse(CamelModel):
    id: int
    symbol: str
    timeframe: Optional[str]
    strategy_name: Optional[str]
    direction: str
    position_size_lots: float
    entry_fill: Optional[float]
    exit_fill: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_amount: Optional[float]
    rr_planned: Optional[float]
    pnl: float
    realized_r: Optional[float]
    result: Optional[str]
    status: str
    market_regime: Optional[str]
    confidence: Optional[float]
    notes: Optional[str]
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None


def _trade_to_response(t: Trade) -> dict:
    return {
        "id": t.id,
        "symbol": t.symbol,
        "timeframe": t.timeframe,
        "strategy_name": t.strategy_name,
        "direction": t.direction,
        "position_size_lots": t.position_size_lots,
        "entry_fill": t.entry_fill,
        "exit_fill": t.exit_fill,
        "stop_loss": t.stop_loss,
        "take_profit": t.take_profit,
        "risk_amount": t.risk_amount,
        "rr_planned": t.rr_planned,
        "pnl": t.pnl or 0.0,
        "realized_r": t.realized_r,
        "result": t.result,
        "status": t.status,
        "market_regime": t.market_regime,
        "confidence": t.confidence,
        "notes": t.notes,
        "opened_at": t.opened_at,
        "closed_at": t.closed_at,
    }


# Legacy recent endpoint (Tested by test_api_routes.py)
@router.get("/recent")
async def get_recent_analyses(
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_token)
):
    q = select(Analysis).order_by(desc(Analysis.created_at)).limit(20)
    res = await db.execute(q)
    items = res.scalars().all()
    return [
        {
            "id": item.id,
            "symbol": item.symbol,
            "timeframe": item.timeframe,
            "direction": item.direction,
            "confidence": item.confidence,
            "bias": item.bias,
            "score_total": item.score_total,
            "summary": item.summary,
            "created_at": item.created_at.isoformat() if item.created_at else None
        }
        for item in items
    ]


# Modern Journal / Trade CRUD Endpoints
@router.post("/trades", response_model=TradeResponse)
async def create_trade(payload: TradeCreate, db: AsyncSession = Depends(get_db)):
    trade = Trade(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        strategy_name=payload.strategy_name,
        direction=payload.direction.upper(),
        position_size_lots=payload.position_size_lots,
        entry_fill=payload.entry_fill,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        risk_amount=payload.risk_amount,
        rr_planned=payload.rr_planned,
        market_regime=payload.market_regime,
        structure_context=payload.structure_context,
        liquidity_context=payload.liquidity_context,
        confidence=payload.confidence,
        notes=payload.notes,
        status="OPEN",
        result="OPEN"
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return _trade_to_response(trade)


@router.get("/trades", response_model=List[TradeResponse])
async def list_trades(
    symbol: Optional[str] = None,
    strategy: Optional[str] = None,
    direction: Optional[str] = None,
    result: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)

    q = select(Trade).order_by(desc(Trade.opened_at))
    if symbol:
        q = q.where(Trade.symbol == symbol.upper())
    if strategy:
        q = q.where(Trade.strategy_name == strategy)
    if direction:
        q = q.where(Trade.direction == direction.upper())
    if result:
        q = q.where(Trade.result == result.upper())
    q = q.offset(safe_offset).limit(safe_limit)
    res = await db.execute(q)
    trades = res.scalars().all()
    return [_trade_to_response(t) for t in trades]


@router.put("/trades/{trade_id}", response_model=TradeResponse)
async def update_trade(trade_id: int, payload: TradeUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = res.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if payload.exit_fill is not None:
        trade.exit_fill = payload.exit_fill
    if payload.pnl is not None:
        trade.pnl = payload.pnl
    if payload.realized_r is not None:
        trade.realized_r = payload.realized_r
    if payload.result is not None:
        trade.result = payload.result.upper()
    if payload.status is not None:
        trade.status = payload.status.upper()
        if trade.status == "CLOSED" and not trade.closed_at:
            trade.closed_at = datetime.now(timezone.utc)
    if payload.notes is not None:
        trade.notes = payload.notes

    await db.commit()
    await db.refresh(trade)
    return _trade_to_response(trade)


@router.delete("/trades/{trade_id}")
async def delete_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = res.scalar_one_or_none()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    await db.delete(trade)
    await db.commit()
    return {"deleted": trade_id}
