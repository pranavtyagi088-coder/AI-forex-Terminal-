"""
Paper Trading Execution Engine.
"""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trade import Trade
from app.models.instrument import Instrument
from app.engines.risk.calculator import calculate_pip_value_usd


@dataclass
class TradeOrderRequest:
    analysis_id: int | None
    symbol: str
    direction: str
    position_size_lots: float
    entry_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    slippage_pips: float = 0.5
    commission_per_lot: float = 7.0


async def execute_paper_order(
    db: AsyncSession,
    order: TradeOrderRequest,
    live_rates: dict[str, float] | None = None,
) -> Trade:
    if live_rates is None:
        live_rates = {}

    result = await db.execute(select(Instrument).where(Instrument.symbol == order.symbol))
    inst = result.scalar_one_or_none()
    if not inst:
        raise ValueError(f"Instrument {order.symbol} not found in database")

    pip_size = float(inst.pip_size)
    slippage_offset = order.slippage_pips * pip_size
    if order.direction == "BUY":
        entry_fill = order.entry_price + slippage_offset
    else:
        entry_fill = order.entry_price - slippage_offset

    total_commission = order.position_size_lots * order.commission_per_lot

    trade = Trade(
        analysis_id=order.analysis_id,
        broker="paper",
        opened_at=datetime.now(timezone.utc),
        position_size_lots=order.position_size_lots,
        entry_fill=entry_fill,
        exit_fill=None,
        pnl=None,
        slippage=order.slippage_pips,
        commission=total_commission,
        status="OPEN",
    )
    db.add(trade)
    await db.commit()
    await db.refresh(trade)
    return trade


async def close_paper_trade(
    db: AsyncSession,
    trade_id: int,
    exit_price: float,
    symbol: str,
    direction: str,
    live_rates: dict[str, float] | None = None,
) -> Trade:
    if live_rates is None:
        live_rates = {}

    result = await db.execute(select(Trade).where(Trade.id == trade_id, Trade.status == "OPEN"))
    trade = result.scalar_one_or_none()
    if not trade:
        raise ValueError(f"Open trade with ID {trade_id} not found")

    inst_result = await db.execute(select(Instrument).where(Instrument.symbol == symbol))
    inst = inst_result.scalar_one_or_none()
    if not inst:
        raise ValueError(f"Instrument {symbol} not found")

    pip_size = float(inst.pip_size)
    contract_size = float(inst.contract_size)
    quote_ccy = inst.quote_currency

    pip_val_usd = calculate_pip_value_usd(pip_size, contract_size, quote_ccy, live_rates)

    entry_fill = float(trade.entry_fill or 0.0)
    if direction == "BUY":
        pips_gained = (exit_price - entry_fill) / pip_size
    else:
        pips_gained = (entry_fill - exit_price) / pip_size

    gross_pnl = float(trade.position_size_lots or 0.0) * pips_gained * pip_val_usd
    net_pnl = gross_pnl - float(trade.commission or 0.0)

    trade.exit_fill = exit_price
    trade.closed_at = datetime.now(timezone.utc)
    trade.pnl = round(net_pnl, 2)
    trade.status = "CLOSED"

    await db.commit()
    await db.refresh(trade)
    return trade
