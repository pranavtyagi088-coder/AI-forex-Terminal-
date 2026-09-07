from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from typing import Optional, List
from datetime import datetime

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

class PropFirmProfileSchema(CamelModel):
    id: str
    name: str
    daily_drawdown_pct: float = 5.0
    max_drawdown_pct: float = 10.0
    drawdown_type: str = "STATIC"
    max_loss_basis: str = "BALANCE"
    profit_target_pct: Optional[float] = 8.0
    min_trading_days: int = 0

class AccountStateSchema(CamelModel):
    account_id: str
    profile_id: str
    starting_balance: float
    current_balance: float
    current_equity: float
    daily_starting_equity: float
    high_water_mark: float
    daily_drawdown_limit_usd: float
    total_drawdown_limit_usd: float
    current_daily_loss_usd: float = 0.0
    current_total_loss_usd: float = 0.0
    status: str = "ACTIVE"
    
    # Provider Adapter Fields
    data_status: str = "UNAVAILABLE"
    last_synced_at: Optional[datetime] = None
    is_verified: bool = False
    provider_name: Optional[str] = None

class TradeCheckRequest(CamelModel):
    pair: str
    order_type: str = "BUY"
    lot_size: float = Field(..., gt=0)
    stop_loss_pips: float = Field(..., gt=0)
    entry_price: float = Field(..., gt=0)

class TradeCheckResult(CamelModel):
    allowed: bool
    risk_amount_usd: float
    risk_pct: float
    projected_daily_loss_pct: float
    projected_total_loss_pct: float
    max_allowed_lot_size: float
    violations: List[str] = []
    warnings: List[str] = []

class AccountHealthScoreSchema(CamelModel):
    score: float
    status: str
    daily_loss_used_pct: float
    total_loss_used_pct: float
    consecutive_losses: int = 0
    rule_breach_imminent: bool = False
    recommendations: List[str] = []
