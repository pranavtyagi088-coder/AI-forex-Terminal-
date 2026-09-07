from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from app.core.database import get_db
from app.services.scanner.market_scanner import (
    MarketScannerService,
    ACTIVE_RADAR_SIGNALS,
    LAST_SCAN_TIMESTAMP,
    DEFAULT_WATCHLIST,
)
from app.services.scanner.ws_manager import ws_manager

router = APIRouter(prefix="/api/scanner", tags=["Market Scanner"])


@router.get("/signals")
async def get_active_signals(limit: int = 20):
    """Retrieve latest high-confluence radar signals."""
    return ACTIVE_RADAR_SIGNALS[:limit]


@router.post("/scan-now")
async def trigger_scan_now(db: AsyncSession = Depends(get_db)):
    """Manually trigger an institutional multi-pair market scan."""
    signals = await MarketScannerService.scan_all(db=db)
    return {
        "status": "success",
        "scanned_at": LAST_SCAN_TIMESTAMP,
        "active_signals_count": len(signals),
        "signals": signals
    }


@router.get("/status")
async def get_scanner_status():
    """Get scanner watchlist and last scan timestamp."""
    return {
        "status": "online",
        "watchlist": DEFAULT_WATCHLIST,
        "total_active_signals": len(ACTIVE_RADAR_SIGNALS),
        "last_scan_at": LAST_SCAN_TIMESTAMP
    }


@router.post("/signals/dismiss/{signal_id}")
async def dismiss_signal(signal_id: str):
    """Dismiss a processed radar signal."""
    global ACTIVE_RADAR_SIGNALS
    initial_len = len(ACTIVE_RADAR_SIGNALS)
    ACTIVE_RADAR_SIGNALS = [s for s in ACTIVE_RADAR_SIGNALS if s.get("id") != signal_id]
    return {
        "status": "dismissed" if len(ACTIVE_RADAR_SIGNALS) < initial_len else "not_found",
        "remaining": len(ACTIVE_RADAR_SIGNALS)
    }


@router.websocket("/ws")
async def scanner_websocket_endpoint(websocket: WebSocket):
    """Live WebSocket connection streaming real-time market radar signals."""
    await ws_manager.connect(websocket)
    try:
        await websocket.send_json({
            "type": "RADAR_INIT",
            "signals": ACTIVE_RADAR_SIGNALS,
            "last_scan_at": LAST_SCAN_TIMESTAMP
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)
