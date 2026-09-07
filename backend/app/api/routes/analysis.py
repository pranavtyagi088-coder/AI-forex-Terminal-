from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from app.core.database import get_db
from app.models.analysis import Analysis
from app.engines.intelligence.orchestrator import MarketIntelligenceOrchestrator
from app.api.routes.webhooks import LATEST_SNAPSHOTS

router = APIRouter(prefix="/api/analysis", tags=["Market Analysis"])
orchestrator = MarketIntelligenceOrchestrator()

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

class AnalysisRunRequest(CamelModel):
    symbol: str = Field("EUR/USD")
    timeframe: str = Field("15")
    direction: str = Field("BUY")
    image_paths: Optional[List[str]] = None
    account_balance: float = 100000.0
    risk_percent: float = 1.0

class AnalysisResponse(CamelModel):
    id: str
    symbol: str
    timeframe: str
    direction: str
    bias: str
    confidence: float
    chart_images: Optional[List[str]] = None
    risk_reward_ratio: Optional[float] = None
    summary: Optional[str] = None
    score_total: Optional[float] = None
    no_trade_reasons: Optional[List[str]] = None
    position_sizing: Optional[Dict[str, Any]] = None
    market_state: Optional[Dict[str, Any]] = None

@router.post("/run", response_model=AnalysisResponse)
async def run_market_analysis(payload: AnalysisRunRequest, db: AsyncSession = Depends(get_db)):
    snap_key = f"{payload.symbol.upper().replace('/', '')}_{payload.timeframe}"
    snapshot = LATEST_SNAPSHOTS.get(snap_key)
    tech_context = snapshot.model_dump() if snapshot else {}

    result = await orchestrator.run_analysis(
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        direction=payload.direction,
        image_paths=payload.image_paths,
        technical_context=tech_context,
        account_balance=payload.account_balance,
        risk_percent=payload.risk_percent,
        db=db
    )

    db_analysis = Analysis(
        id=result["id"],
        symbol=result["symbol"],
        timeframe=result["timeframe"],
        direction=result["direction"],
        confidence=result["confidence"],
        bias=result["bias"],
        risk_reward_ratio=result["risk_reward_ratio"],
        chart_images=result.get("chart_images", payload.image_paths or []),
        summary=result["summary"],
        score_total=result.get("score_total"),
        no_trade_reasons=result.get("no_trade_reasons")
    )
    db.add(db_analysis)
    await db.commit()
    await db.refresh(db_analysis)

    response_data = {
        "id": db_analysis.id,
        "symbol": db_analysis.symbol,
        "timeframe": db_analysis.timeframe,
        "direction": db_analysis.direction,
        "bias": db_analysis.bias,
        "confidence": db_analysis.confidence,
        "chart_images": db_analysis.chart_images,
        "risk_reward_ratio": db_analysis.risk_reward_ratio,
        "summary": db_analysis.summary,
        "score_total": db_analysis.score_total,
        "no_trade_reasons": db_analysis.no_trade_reasons,
        "position_sizing": result.get("position_sizing"),
        "market_state": result.get("market_state")
    }
    return response_data
