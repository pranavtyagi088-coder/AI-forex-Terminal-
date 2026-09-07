"""Risk calculator endpoint - fixed pip-value logic."""

from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import verify_api_token
from app.core.database import get_db
from app.engines.risk.calculator import MissingRateError, RiskRequest, calculate_position_size
from app.services.market.data_service import get_instrument_by_symbol

router = APIRouter(prefix="/api/risk", tags=["risk"])


class RiskCalcRequest(BaseModel):
    symbol: str
    account_balance: float
    risk_percent: float
    entry: float
    stop_loss: float
    take_profit_1: float
    leverage: float
    take_profit_2: float | None = None


@router.post("/calculate")
async def calculate_risk(
    req: RiskCalcRequest,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token),
):
    instrument = await get_instrument_by_symbol(db, req.symbol)
    if not instrument:
        raise HTTPException(404, f"Instrument {req.symbol} not found")

    risk_req = RiskRequest(
        account_balance=req.account_balance, risk_percent=req.risk_percent,
        entry=req.entry, stop_loss=req.stop_loss, take_profit_1=req.take_profit_1,
        take_profit_2=req.take_profit_2, leverage=req.leverage,
        pip_size=float(instrument.pip_size), contract_size=float(instrument.contract_size),
        quote_currency=instrument.quote_currency,
    )

    live_rates: dict[str, float] = {}
    try:
        result = calculate_position_size(risk_req, live_rates)
    except MissingRateError as e:
        raise HTTPException(422, f"Missing live exchange rate for {e}.")
    except ValueError as e:
        raise HTTPException(422, str(e))

    return result
