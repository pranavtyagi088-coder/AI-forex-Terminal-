"""
WebSocket Telemetry Endpoint — /ws/telemetry
Real-time push channel for the institutional cockpit.
Auth-gated via query param (browser WS standard).
Golden Rule #7: Safety > Automation.
Golden Rule #8: AI is SIDECAR — transport only, no decision authority.
"""
import uuid
import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.config import settings
from app.engines.telemetry.ws_manager import ws_manager

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


def _verify_ws_token(token: str) -> bool:
    """Deterministic token check."""
    if not token or not token.strip():
        return False
    return token.strip() == settings.API_AUTH_TOKEN


@router.websocket("/ws/telemetry")
async def ws_telemetry_stream(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    # ── AUTH GATE (Fail-Closed) ──
    if not _verify_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized: invalid or missing token")
        return

    client_id = f"ws_{uuid.uuid4().hex[:12]}"

    await websocket.accept()
    await ws_manager.connect(websocket, client_id)

    # ── Welcome Handshake ──
    await websocket.send_json({
        "type": "SYSTEM",
        "severity": "INFO",
        "source": "ws_telemetry",
        "message": "Connected to AI Forex Terminal — real-time telemetry stream",
        "client_id": client_id,
        "active_connections": ws_manager.get_active_count(),
        "timestamp": time.time(),
    })

    # ── Client Command Loop ──
    try:
        while True:
            raw = await websocket.receive_text()

            if raw == "ping":
                await websocket.send_json({
                    "type": "PONG",
                    "client_id": client_id,
                    "timestamp": time.time(),
                })

            elif raw == "status":
                await websocket.send_json({
                    "type": "STATUS",
                    "client_id": client_id,
                    "active_connections": ws_manager.get_active_count(),
                    "all_clients": ws_manager.get_client_ids(),
                    "timestamp": time.time(),
                })

            elif raw == "snapshot":
                from app.engines.telemetry.hub import telemetry_hub
                snap = telemetry_hub.get_snapshot()
                await websocket.send_json({
                    "type": "SNAPSHOT",
                    "client_id": client_id,
                    "data": snap,
                    "timestamp": time.time(),
                })

            else:
                await websocket.send_json({
                    "type": "ERROR",
                    "severity": "WARN",
                    "message": f"Unknown command: {raw[:50]}",
                    "timestamp": time.time(),
                })

    except WebSocketDisconnect:
        await ws_manager.disconnect(client_id)
    except Exception as exc:
        logger.error("WS connection terminated for %s: %s", client_id, exc)
        await ws_manager.disconnect(client_id)
