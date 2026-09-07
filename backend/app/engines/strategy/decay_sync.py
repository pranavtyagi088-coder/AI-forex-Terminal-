"""
Real Decay Sync — Bridges Trade Journal DB data to DecayDetector.
Replaces runtime metadata map with actual historical performance.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.trade import Trade
from app.engines.strategy.decay_detector import DecayDetector
from app.engines.strategy.performance_aggregator import compute_strategy_performance


async def get_strategy_decay_from_db(
    db: AsyncSession,
    strategy_name: str
) -> Dict[str, Any]:
    """
    Fetches all closed trades for a strategy from DB,
    computes real metrics, and returns decay status.
    """
    q = select(Trade).where(
        Trade.strategy_name == strategy_name,
        Trade.status == "CLOSED"
    )
    res = await db.execute(q)
    trades = res.scalars().all()

    if not trades:
        return {
            "strategy_name": strategy_name,
            "decay_status": "ACTIVE",
            "total_trades": 0,
            "sample_reliable": False,
            "warnings": []
        }

    metrics = DecayDetector.compute_metrics(trades, current_lifecycle="ACTIVE")
    return {
        "strategy_name": strategy_name,
        "decay_status": metrics.lifecycle_status,
        "total_trades": metrics.total_trades,
        "win_rate": metrics.win_rate,
        "avg_r": metrics.avg_realized_r,
        "profit_factor": metrics.profit_factor,
        "max_drawdown_pct": metrics.max_drawdown_pct,
        "consecutive_losses": metrics.consecutive_losses,
        "sample_reliable": metrics.total_trades >= DecayDetector.MIN_TRADES_FOR_EVAL,
        "warnings": metrics.decay_warnings
    }


def compute_decay_from_trade_dicts(
    trades: List[Dict[str, Any]],
    strategy_name: str = "UNKNOWN"
) -> Dict[str, Any]:
    """
    Pure function for testing — computes decay from trade dicts
    without requiring DB connection.
    """
    perf = compute_strategy_performance(strategy_name, trades)

    if perf.total_trades == 0:
        return {"decay_status": "ACTIVE", "sample_reliable": False}

    # Map performance to decay status
    status = "HEALTHY"
    warnings = []

    if perf.total_trades < 5:
        status = "ACTIVE"
        warnings.append("Insufficient sample size for reliable decay assessment")
    elif perf.win_rate < 32.0:
        status = "DEGRADED"
        warnings.append(f"Severe win rate decay: {perf.win_rate}%")
    elif perf.win_rate < 42.0:
        status = "WATCH"
        warnings.append(f"Mild win rate drop: {perf.win_rate}%")

    if perf.expectancy < -0.2 and perf.total_trades >= 5:
        status = "DEGRADED"
        warnings.append(f"Negative expectancy: {perf.expectancy}R")

    if perf.max_drawdown_pct >= 25.0:
        status = "SUSPENDED"
        warnings.append(f"Critical drawdown: {perf.max_drawdown_pct}%")

    if perf.max_consecutive_losses >= 7 and perf.total_trades >= 10:
        if status == "HEALTHY":
            status = "WATCH"
        warnings.append(f"Loss streak: {perf.max_consecutive_losses}")

    return {
        "decay_status": status,
        "sample_reliable": perf.total_trades >= 10,
        "total_trades": perf.total_trades,
        "win_rate": perf.win_rate,
        "expectancy": perf.expectancy,
        "profit_factor": perf.profit_factor,
        "max_drawdown_pct": perf.max_drawdown_pct,
        "warnings": warnings
    }


def build_decay_map_from_trades(
    all_closed_trades: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Builds a {strategy_name: decay_status} map from all closed trades.
    Used by Strategy Matcher for real decay integration.
    """
    from collections import defaultdict
    grouped = defaultdict(list)
    for t in all_closed_trades:
        sname = t.get("strategy_name") or "UNKNOWN"
        grouped[sname].append(t)

    decay_map = {}
    for sname, trades in grouped.items():
        result = compute_decay_from_trade_dicts(trades, sname)
        decay_map[sname] = result["decay_status"]

    return decay_map


async def fetch_all_closed_trades_from_db(db: AsyncSession) -> List[Dict[str, Any]]:
    """Fetches all closed trades from DB and returns them as a list of dicts."""
    q = select(Trade).where(Trade.status == "CLOSED")
    res = await db.execute(q)
    trades = res.scalars().all()
    return [
        {
            "id": t.id,
            "strategy_name": t.strategy_name,
            "pnl": t.pnl or 0.0,
            "realized_r": t.realized_r or 0.0,
            "result": t.result,
            "status": t.status,
            "opened_at": t.opened_at,
            "closed_at": t.closed_at
        }
        for t in trades
    ]


async def build_decay_map_from_db(db: AsyncSession) -> Dict[str, str]:
    """Queries all closed trades from DB and returns {strategy_name: decay_status} map."""
    trades = await fetch_all_closed_trades_from_db(db)
    return build_decay_map_from_trades(trades)
