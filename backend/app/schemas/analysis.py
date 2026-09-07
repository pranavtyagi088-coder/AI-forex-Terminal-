"""Pydantic schemas for the analysis API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    symbol: str = Field(..., examples=["EUR/USD"])
    timeframe: str = Field(default="1H", examples=["1H", "4H", "15M"])
    entry: float | None = None
    stop_loss: float | None = None
    take_profit_1: float | None = None
    take_profit_2: float | None = None
    image_path: str | None = Field(default=None, description="Optional chart screenshot filename in uploads/")
    news_risk: str = Field(default="none", pattern="^(none|low|medium|high)$")
    timeframe_conflicts: int = Field(default=0, ge=0)


class ScoreBreakdownResponse(BaseModel):
    trend: float
    structure: float
    momentum: float
    support_resistance: float
    liquidity: float
    volume: float
    ai_cross_check: float
    volatility_penalty: float
    timeframe_conflict_penalty: float
    news_risk_penalty: float


class AnalysisResponse(BaseModel):
    symbol: str
    signal: str
    bias: str
    score_total: float
    score_breakdown: ScoreBreakdownResponse
    data_source: str
    rr_ratio: float | None = None
    veto_reasons: list[str] = []
    ai_explanation: str | None = None
    technical_summary: dict
