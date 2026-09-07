from typing import Dict, Any, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class ScoreBreakdown(BaseModel):
    model_config = ConfigDict(extra="allow")
    technical: float = 70.0
    macro: float = 70.0
    sentiment: float = 70.0
    ai_cross_check: float = 0.0
    volatility_penalty: float = 0.0

class ScoringResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    total: float = 75.0
    total_score: float = 75.0
    bias: str = "bullish"
    signal: str = "BUY"
    confidence: float = 0.80
    vetoed: bool = False
    no_trade_reasons: List[str] = Field(default_factory=list)
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)

class ConfluenceScore(ScoringResult):
    pass

def calculate_confluence_score(snap: Any, ai_agrees: Optional[bool] = None, *args, **kwargs) -> ScoringResult:
    if hasattr(snap, "trend_direction"):
        trend = snap.trend_direction
        atr = getattr(snap, "atr", 0.001)
        base_score = 70.0 if trend in ["bullish", "bearish"] else 40.0
    else:
        trend = "bullish"
        atr = 0.001
        base_score = 70.0
        
    ai_bonus = 10.0 if ai_agrees is True else (0.0 if ai_agrees is None else -10.0)
    vol_penalty = -15.0 if atr > 3.0 else 0.0
    
    total = base_score + ai_bonus + vol_penalty
    total = max(0.0, min(100.0, total))
    
    breakdown = ScoreBreakdown(
        technical=base_score,
        macro=70.0,
        sentiment=70.0,
        ai_cross_check=ai_bonus,
        volatility_penalty=vol_penalty
    )
    
    return ScoringResult(
        total=total,
        total_score=total,
        bias=trend if trend in ["bullish", "bearish"] else "neutral",
        signal="BUY" if trend == "bullish" else "SELL" if trend == "bearish" else "NEUTRAL",
        confidence=round(total / 100.0, 2),
        breakdown=breakdown
    )

def calculate_score(*args, **kwargs) -> ScoringResult:
    return calculate_confluence_score(*args, **kwargs)
