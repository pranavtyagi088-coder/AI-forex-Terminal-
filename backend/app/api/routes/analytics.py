from __future__ import annotations
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.trade import Trade
from app.models.strategy import Strategy
from app.engines.analytics.metrics import (
    QuantitativeAnalyticsEngine,
    RollingPerformanceMetrics,
    SlippagePostMortem,
)
from app.engines.analytics.rebalancer import (
    AdaptiveWeightRebalancer,
    StrategyWeightAllocation,
)

router = APIRouter(prefix="/api/analytics", tags=["Advanced Analytics"])


@router.get("/rolling-metrics", response_model=RollingPerformanceMetrics)
async def get_rolling_risk_metrics(
    strategy_id: Optional[int] = Query(None, description="Filter by strategy ID"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Trade).where(Trade.status == "CLOSED")
    if strategy_id is not None:
        stmt = stmt.where(Trade.strategy_id == strategy_id)
    stmt = stmt.order_by(Trade.opened_at.desc()).limit(limit)

    result = await db.execute(stmt)
    trades = result.scalars().all()

    # Chronological order for metrics
    trades = list(reversed(trades))
    pnls = [float(t.pnl or 0.0) for t in trades]
    r_multiples = [float(t.realized_r or 0.0) for t in trades if t.realized_r is not None]

    return QuantitativeAnalyticsEngine.calculate_rolling_metrics(
        pnls=pnls,
        r_multiples=r_multiples,
    )


@router.get("/slippage-report", response_model=SlippagePostMortem)
async def get_slippage_post_mortem(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Trade).where(Trade.status == "CLOSED").order_by(Trade.opened_at.desc()).limit(limit)
    result = await db.execute(stmt)
    trades = result.scalars().all()

    slippages = [float(t.slippage or 0.0) for t in trades]
    return QuantitativeAnalyticsEngine.analyze_slippage_records(slippages)


@router.get("/strategy-weights", response_model=List[StrategyWeightAllocation])
async def get_adaptive_strategy_weights(
    db: AsyncSession = Depends(get_db),
):
    strat_stmt = select(Strategy)
    strat_res = await db.execute(strat_stmt)
    strategies = strat_res.scalars().all()

    allocations: List[StrategyWeightAllocation] = []

    for s in strategies:
        trade_stmt = select(Trade).where(Trade.strategy_id == s.id, Trade.status == "CLOSED")
        trade_res = await db.execute(trade_stmt)
        trades = trade_res.scalars().all()

        pnls = [float(t.pnl or 0.0) for t in trades]
        r_mults = [float(t.realized_r or 0.0) for t in trades if t.realized_r is not None]
        metrics = QuantitativeAnalyticsEngine.calculate_rolling_metrics(pnls, r_mults)

        alloc = AdaptiveWeightRebalancer.evaluate_strategy_weight(
            strategy_id=str(s.id),
            strategy_name=s.name,
            metrics=metrics,
            current_status=getattr(s, "lifecycle_status", "ACTIVE"),
        )
        allocations.append(alloc)

    return allocations
