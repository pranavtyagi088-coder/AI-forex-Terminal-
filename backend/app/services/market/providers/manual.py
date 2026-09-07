import pandas as pd
from datetime import datetime
from typing import Optional
from app.core.data_status import DataStatus
from .base import MarketDataProvider, PriceResult, OHLCVResult

class ManualMarketProvider(MarketDataProvider):
    """Handles manually entered market data from the UI"""
    
    async def fetch_price(self, symbol: str, **kwargs) -> PriceResult:
        manual_price = kwargs.get("manual_price")
        if not manual_price:
            return PriceResult(
                symbol=symbol, price=0.0, status=DataStatus.UNAVAILABLE, 
                source="MANUAL", timestamp=datetime.now(timezone.utc).isoformat()
            )
            
        return PriceResult(
            symbol=symbol,
            price=float(manual_price),
            status=DataStatus.USER_UPLOAD,
            source="MANUAL",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100, **kwargs) -> OHLCVResult:
        # Manual provider does not supply OHLCV history natively, 
        # it relies on the user providing a CSV or just using live prices.
        return OHLCVResult(
            symbol=symbol, timeframe=timeframe, data=None,
            status=DataStatus.UNAVAILABLE, source="MANUAL"
        )
