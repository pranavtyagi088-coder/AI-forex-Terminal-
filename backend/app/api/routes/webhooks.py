from fastapi import APIRouter, HTTPException, status, Header, Query
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid

from app.schemas.market_data import PineAlertPayload, TimeframeSnapshot, MarketStateStructure
from app.core.config import settings

router = APIRouter(prefix="/api/webhooks", tags=["TradingView Webhooks"])

# In-memory storage for latest snapshots per symbol/timeframe
LATEST_SNAPSHOTS: Dict[str, TimeframeSnapshot] = {}

# In-memory ring buffer for recent alerts feed (max 50)
RECENT_ALERTS: List[Dict[str, Any]] = []
MAX_ALERTS = 50


def _infer_suggested_direction(event_type: str, ext_bias: int) -> str:
    evt = event_type.upper()
    if "BULL" in evt or "BUY" in evt or "SWEEP_LOW" in evt:
        return "BUY"
    if "BEAR" in evt or "SELL" in evt or "SWEEP_HIGH" in evt:
        return "SELL"
    if ext_bias > 0:
        return "BUY"
    if ext_bias < 0:
        return "SELL"
    return "BUY"


@router.post("/tradingview", response_model=TimeframeSnapshot, status_code=status.HTTP_200_OK)
async def receive_tradingview_alert(
    payload: PineAlertPayload,
    x_webhook_secret: Optional[str] = Header(None)
):
    # Validate secret if configured
    if payload.secret_token and payload.secret_token != settings.API_AUTH_TOKEN:
        if x_webhook_secret and x_webhook_secret != settings.API_AUTH_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook secret token"
            )

    now_utc = datetime.now(timezone.utc)

    # Convert Pine Alert payload to deterministic TimeframeSnapshot
    snapshot = TimeframeSnapshot(
        symbol=payload.symbol.upper(),
        timeframe=payload.timeframe,
        chart_observed_at=now_utc,
        event_type=payload.event,
        price=payload.price,
        atr=payload.atr,
        structure=MarketStateStructure(
            ext_bias=payload.ext_bias or 0,
            int_bias=payload.int_bias or 0,
            regime=payload.regime or "NORMAL",
            session=payload.session or "OFF"
        ),
        provenance="TRADINGVIEW_WEBHOOK"
    )

    # Store latest snapshot for quick AI Vision correlation
    key = f"{snapshot.symbol}_{snapshot.timeframe}"
    LATEST_SNAPSHOTS[key] = snapshot

    # Record into Alerts Feed (strictly informational - does NOT auto-execute)
    alert_item = {
        "id": str(uuid.uuid4())[:8],
        "symbol": snapshot.symbol,
        "timeframe": snapshot.timeframe,
        "event": snapshot.event_type,
        "price": snapshot.price,
        "atr": snapshot.atr,
        "suggested_direction": _infer_suggested_direction(snapshot.event_type, payload.ext_bias or 0),
        "regime": payload.regime or "NORMAL",
        "session": payload.session or "OFF",
        "received_at": now_utc.isoformat(),
        "status": "NEW"
    }

    RECENT_ALERTS.insert(0, alert_item)
    if len(RECENT_ALERTS) > MAX_ALERTS:
        RECENT_ALERTS.pop()

    return snapshot


@router.get("/snapshots/{symbol}/{timeframe}", response_model=TimeframeSnapshot)
async def get_latest_snapshot(symbol: str, timeframe: str):
    key = f"{symbol.upper()}_{timeframe}"
    snapshot = LATEST_SNAPSHOTS.get(key)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No market snapshot observed for {symbol} on {timeframe}"
        )
    return snapshot


@router.get("/alerts")
async def get_recent_alerts(limit: int = Query(20, ge=1, le=50)):
    """Retrieve recent TradingView alert stream for dashboard notification."""
    return RECENT_ALERTS[:limit]


@router.post("/alerts/clear")
async def clear_alerts():
    """Clear alert feed history."""
    RECENT_ALERTS.clear()
    return {"status": "cleared", "count": 0}
