from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class NoTradeResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    should_trade: bool = True
    vetoed: bool = False
    reasons: List[str] = Field(default_factory=list)

def evaluate_no_trade(result: Any, snap: Any = None, rr_ratio: float = 2.0, *args, **kwargs) -> NoTradeResult:
    reasons = []
    total = getattr(result, "total", 75.0)
    if total < 60.0:
        reasons.append("LOW_CONFLUENCE_SCORE")
    if rr_ratio < 1.0:
        reasons.append("RR_RATIO_BELOW_MINIMUM (RR < 1.0)")
        
    should_trade = len(reasons) == 0
    return NoTradeResult(should_trade=should_trade, vetoed=not should_trade, reasons=reasons)
