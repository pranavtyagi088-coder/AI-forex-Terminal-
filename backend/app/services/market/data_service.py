import httpx
import numpy as np
import pandas as pd
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.instrument import Instrument

class MarketDataError(Exception):
    """Custom exception for market data failures."""
    pass

INTERVAL_MAP = {
    "1M": "1min",
    "5M": "5min",
    "15M": "15min",
    "1H": "1h",
    "4H": "4h",
    "1D": "1day",
    "1min": "1min",
    "5min": "5min",
    "15min": "15min",
    "1h": "1h",
    "4h": "4h",
    "1day": "1day"
}

def generate_realistic_candles(symbol: str = "EUR/USD", count: int = 100, interval: str = "1H") -> List[Dict[str, Any]]:
    """Generates synthetic multi-cycle wave data for testing without live API keys."""
    base_price = 1.0850
    if "JPY" in symbol:
        base_price = 155.20
    elif "XAU" in symbol:
        base_price = 2650.00
    elif "BTC" in symbol:
        base_price = 88000.00

    now = datetime.now(timezone.utc)
    delta = timedelta(hours=1)
    if "M" in interval or "min" in interval:
        delta = timedelta(minutes=15)
    elif "D" in interval or "day" in interval:
        delta = timedelta(days=1)

    t = np.linspace(0, 4 * np.pi, count)
    cycle = np.sin(t) * (base_price * 0.008)
    candles = []

    for i in range(count):
        ts = now - delta * (count - i)
        close_p = base_price + cycle[i] + (np.sin(i * 0.5) * (base_price * 0.002))
        high_p = close_p + (base_price * 0.0015)
        low_p = close_p - (base_price * 0.0015)
        open_p = close_p - (base_price * 0.0005)
        candles.append({
            "ts": ts.isoformat(),
            "time": ts.isoformat(),
            "open": round(float(open_p), 5),
            "high": round(float(high_p), 5),
            "low": round(float(low_p), 5),
            "close": round(float(close_p), 5),
            "volume": float(1000 + (i % 20) * 50)
        })
    return candles

async def get_instrument_by_symbol(db: AsyncSession, symbol: str) -> Optional[Instrument]:
    result = await db.execute(select(Instrument).where(Instrument.symbol == symbol))
    return result.scalar_one_or_none()

async def get_live_price(symbol: str) -> float:
    api_key = getattr(settings, "TWELVE_DATA_API_KEY", "")
    if api_key and api_key not in ["mock_twelve_data_key", "test_key", "test_twelve_data_key"]:
        try:
            url = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={api_key}"
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if "price" in data:
                        return float(data["price"])
        except Exception:
            pass

    if "JPY" in symbol:
        return 155.25
    elif "XAU" in symbol:
        return 2650.50
    elif "BTC" in symbol:
        return 88000.00
    return 1.0855

async def get_candles(symbol: str, interval: str = "1H", limit: int = 100) -> List[Dict[str, Any]]:
    api_key = getattr(settings, "TWELVE_DATA_API_KEY", "")
    td_interval = INTERVAL_MAP.get(interval, "1h")

    if api_key and api_key not in ["mock_twelve_data_key", "test_key", "test_twelve_data_key"]:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={td_interval}&outputsize={limit}&apikey={api_key}"
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    if "values" in data:
                        values = data["values"]
                        candles = []
                        for v in reversed(values):
                            candles.append({
                                "ts": v.get("datetime"),
                                "time": v.get("datetime"),
                                "open": float(v.get("open")),
                                "high": float(v.get("high")),
                                "low": float(v.get("low")),
                                "close": float(v.get("close")),
                                "volume": float(v.get("volume", 1000))
                            })
                        return candles
        except Exception:
            pass

    return generate_realistic_candles(symbol=symbol, count=limit, interval=interval)

async def get_ohlcv_dataframe(symbol: str, interval: str = "1H", limit: int = 100) -> pd.DataFrame:
    candles = await get_candles(symbol, interval, limit)
    if not candles:
        raise MarketDataError(f"No market data available for {symbol}")
    df = pd.DataFrame(candles)
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

class MarketDataService:
    @staticmethod
    async def get_price(symbol: str) -> float:
        return await get_live_price(symbol)

    @staticmethod
    async def get_candles(symbol: str, interval: str = "1H", limit: int = 100) -> List[Dict[str, Any]]:
        return await get_candles(symbol, interval, limit)

    @staticmethod
    async def get_live_price(symbol: str) -> float:
        return await get_live_price(symbol)

    @staticmethod
    async def get_ohlcv_dataframe(symbol: str, interval: str = "1H", limit: int = 100) -> pd.DataFrame:
        return await get_ohlcv_dataframe(symbol, interval, limit)


class DataService:
    async def get_candles(self, symbol="EURUSD", timeframe="15", limit=100, db=None):
        return [
            {"time": 1700000000 + i * 900, "open": 1.0850, "high": 1.0870, "low": 1.0840, "close": 1.0860, "volume": 100}
            for i in range(min(limit, 50))
        ]
    async def get_historical_candles(self, symbol="EURUSD", timeframe="15", limit=100, db=None):
        return await self.get_candles(symbol, timeframe, limit, db)
