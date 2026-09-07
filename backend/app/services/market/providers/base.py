from typing import Protocol, Optional
import pandas as pd
from dataclasses import dataclass
from app.core.data_status import DataStatus

@dataclass
class PriceResult:
    symbol: str
    price: float
    status: DataStatus
    source: str
    timestamp: str

@dataclass
class OHLCVResult:
    symbol: str
    timeframe: str
    data: Optional[pd.DataFrame]
    status: DataStatus
    source: str

class MarketDataProvider(Protocol):
    """Universal interface for all market data providers (Live, Manual, CSV, MT5)"""
    
    async def fetch_price(self, symbol: str, **kwargs) -> PriceResult:
        ...
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100, **kwargs) -> OHLCVResult:
        ...
