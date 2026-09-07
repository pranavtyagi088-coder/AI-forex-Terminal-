import os
import pandas as pd
from datetime import datetime
from app.core.data_status import DataStatus
from .base import MarketDataProvider, PriceResult, OHLCVResult

class CSVMarketProvider(MarketDataProvider):
    """Reads historical data from uploaded CSV files for backtesting/analysis"""
    
    def __init__(self, upload_dir: str = "uploads"):
        self.upload_dir = upload_dir

    async def fetch_price(self, symbol: str, **kwargs) -> PriceResult:
        filename = kwargs.get("csv_filename")
        if not filename:
            return PriceResult(symbol, 0.0, DataStatus.UNAVAILABLE, "CSV", datetime.now(timezone.utc).isoformat())
            
        filepath = os.path.join(self.upload_dir, filename)
        if not os.path.exists(filepath):
            return PriceResult(symbol, 0.0, DataStatus.UNAVAILABLE, "CSV", datetime.now(timezone.utc).isoformat())
            
        try:
            df = pd.read_csv(filepath)
            # Assuming standard OHLC format, grab the last close price
            latest_price = float(df['close'].iloc[-1])
            return PriceResult(symbol, latest_price, DataStatus.USER_UPLOAD, "CSV", datetime.now(timezone.utc).isoformat())
        except Exception:
            return PriceResult(symbol, 0.0, DataStatus.UNAVAILABLE, "CSV", datetime.now(timezone.utc).isoformat())
            
    async def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 100, **kwargs) -> OHLCVResult:
        filename = kwargs.get("csv_filename")
        if not filename:
            return OHLCVResult(symbol, timeframe, None, DataStatus.UNAVAILABLE, "CSV")
            
        filepath = os.path.join(self.upload_dir, filename)
        if not os.path.exists(filepath):
            return OHLCVResult(symbol, timeframe, None, DataStatus.UNAVAILABLE, "CSV")
            
        try:
            df = pd.read_csv(filepath)
            # Standardize columns for the engine
            df.columns = [c.lower() for c in df.columns]
            if len(df) > limit:
                df = df.tail(limit).reset_index(drop=True)
                
            return OHLCVResult(symbol, timeframe, df, DataStatus.USER_UPLOAD, "CSV")
        except Exception:
            return OHLCVResult(symbol, timeframe, None, DataStatus.UNAVAILABLE, "CSV")
