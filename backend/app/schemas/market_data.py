from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

class OHLCVBar(CamelModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

class MarketStateStructure(CamelModel):
    ext_bias: int = 0
    int_bias: int = 0
    alignment: str = "NEUTRAL"
    regime: str = "RANGE"
    session: str = "OFF"
    location: str = "EQUILIBRIUM"
    active_fvg_count: int = 0
    active_ob_count: int = 0

class TimeframeSnapshot(CamelModel):
    symbol: str
    timeframe: str
    chart_observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    bar_timestamp: Optional[datetime] = None
    event_type: str = "PERIODIC_SNAPSHOT"
    price: float = Field(..., gt=0)
    atr: float = Field(..., ge=0)
    structure: MarketStateStructure = Field(default_factory=MarketStateStructure)
    provenance: str = "TRADINGVIEW_WEBHOOK"
    metadata: Dict[str, Any] = {}

class PineAlertPayload(CamelModel):
    symbol: str
    timeframe: str
    event: str
    price: float
    atr: float = 0.0
    ext_bias: Optional[int] = 0
    int_bias: Optional[int] = 0
    regime: Optional[str] = "NORMAL"
    session: Optional[str] = "OFF"
    secret_token: Optional[str] = None
