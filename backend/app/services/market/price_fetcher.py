import httpx
import pandas as pd
from typing import Optional
from dataclasses import dataclass
from app.core.data_status import DataStatus
from app.core.config import settings

@dataclass
class OHLCVResult:
    symbol: str
    timeframe: str
    data: Optional[pd.DataFrame]
    status: DataStatus

async def fetch_ohlcv_twelve_data(symbol: str, timeframe: str = "1H", limit: int = 100) -> OHLCVResult:
    # If no API key configured, return simulated/fallback empty
    if not settings.TWELVE_DATA_API_KEY:
        return OHLCVResult(symbol, timeframe, None, DataStatus.UNAVAILABLE)
        
    try:
        # Standard interval conversion
        interval_map = {"1M": "1min", "15M": "15min", "1H": "1h", "4H": "4h", "1D": "1day"}
        interval = interval_map.get(timeframe, "1h")
        
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&outputsize={limit}&apikey={settings.TWELVE_DATA_API_KEY}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url)
            if res.status_code == 200:
                data = res.json()
                values = data.get("values", [])
                if values:
                    df = pd.DataFrame(values)
                    df['close'] = df['close'].astype(float)
                    df['open'] = df['open'].astype(float)
                    df['high'] = df['high'].astype(float)
                    df['low'] = df['low'].astype(float)
                    df['volume'] = df['volume'].astype(float) if 'volume' in df else 0.0
                    df = df.iloc[::-1].reset_index(drop=True)  # oldest to newest
                    return OHLCVResult(symbol, timeframe, df, DataStatus.LIVE)
    except Exception:
        pass
        
    return OHLCVResult(symbol, timeframe, None, DataStatus.UNAVAILABLE)
