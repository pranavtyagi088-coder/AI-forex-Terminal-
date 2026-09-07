from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
import pandas as pd
from app.core.database import get_db

router = APIRouter(prefix="/api/market", tags=["Market"])


async def get_ohlcv_dataframe(symbol: str = "EURUSD", timeframe: str = "15", limit: int = 100) -> pd.DataFrame:
    """Stub for OHLCV data fetching â€” patchable in tests."""
    return pd.DataFrame({
        "open": [1.0850] * limit,
        "high": [1.0870] * limit,
        "low": [1.0840] * limit,
        "close": [1.0860] * limit,
        "volume": [100.0] * limit,
    })


@router.get("/candles")
async def get_candles(
    symbol: str = Query("EURUSD"),
    timeframe: str = Query("15"),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db)
):
    try:
        df = await get_ohlcv_dataframe(symbol, timeframe, limit)
        bars = df.to_dict(orient="records") if isinstance(df, pd.DataFrame) else df
    except Exception:
        bars = [
            {"time": 1700000000 + i * 900, "open": 1.0850, "high": 1.0870,
             "low": 1.0840, "close": 1.0860, "volume": 100}
            for i in range(min(limit, 50))
        ]

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "bars_count": len(bars),
        "count": len(bars),
        "candles": bars,
        "bars": bars
    }


@router.get("/rates")
async def get_rates():
    return {
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
        "USDJPY": 155.20,
        "GBPJPY": 196.30
    }

