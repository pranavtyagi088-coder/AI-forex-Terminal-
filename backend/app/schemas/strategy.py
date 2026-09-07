from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class UseStrategyRequest(BaseModel):
    strategy_id: str = Field(..., description="UUID of the selected strategy")
    symbol: str = Field(..., description="Instrument symbol e.g. EUR/USD")
    account_balance: float = Field(default=10000.0, ge=100.0, description="Account balance in USD")
    risk_percent: float = Field(default=1.0, ge=0.1, le=5.0, description="Risk percentage per trade")
    direction: Optional[str] = Field(default=None, description="Optional override: BUY or SELL")

class UseStrategyResponse(BaseModel):
    strategy_id: str
    strategy_name: str
    symbol: str
    evidence_grade: str
    decision: str # TRADE, WAIT, NO_TRADE
    is_safe: bool
    blocking_reasons: List[str]
    trade_parameters: Optional[Dict[str, Any]] = None
    mtf_validation: Dict[str, Any]
    market_state_snapshot: Dict[str, Any]
    log_id: str
