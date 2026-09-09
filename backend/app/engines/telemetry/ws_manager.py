"""
WebSocket Connection Manager — Real-Time Telemetry Streaming.
Institutional-grade: Auth-gated, heartbeat-monitored, auto-cleanup.
Golden Rule #7: Safety > Automation (stale connections get killed).
"""
import asyncio
import time
import logging
from typing import Dict, Any, Union
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Manages authenticated WebSocket connections for telemetry broadcast.
    Thread-safe via asyncio.Lock. Auto-cleans stale/dead connections.
    """

    def __init__(
        self,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 10.0,
    ):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self._heartbeat_task: asyncio.Task | None = None

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        async with self._lock:
            if client_id in self.active_connections:
                old_ws = self.active_connections[client_id]
                try:
                    await old_ws.close(code=1000, reason="Replaced by new connection")
                except Exception:
                    pass
            self.active_connections[client_id] = websocket
        logger.info("WS connected: %s | Active: %d", client_id, len(self.active_connections))

    async def disconnect(self, client_id: str) -> None:
        async with self._lock:
            removed = self.active_connections.pop(client_id, None)
        if removed:
            logger.info("WS disconnected: %s | Active: %d", client_id, len(self.active_connections))

    async def broadcast(self, event_data: Union[dict, Any]) -> int:
        if hasattr(event_data, "model_dump"):
            payload = event_data.model_dump()
        elif isinstance(event_data, dict):
            payload = event_data
        else:
            payload = {"data": str(event_data)}

        dead_clients: list[str] = []
        delivered = 0

        async with self._lock:
            snapshot = dict(self.active_connections)

        for client_id, ws in snapshot.items():
            try:
                await ws.send_json(payload)
                delivered += 1
            except Exception:
                dead_clients.append(client_id)

        for cid in dead_clients:
            await self.disconnect(cid)

        return delivered

    async def send_personal(self, client_id: str, data: dict) -> bool:
        async with self._lock:
            ws = self.active_connections.get(client_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception:
            await self.disconnect(client_id)
            return False

    def get_active_count(self) -> int:
        return len(self.active_connections)

    def get_client_ids(self) -> list[str]:
        return list(self.active_connections.keys())

    async def start_heartbeat(self) -> None:
        async def _loop() -> None:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                dead: list[str] = []
                async with self._lock:
                    snapshot = dict(self.active_connections)
                for cid, ws in snapshot.items():
                    try:
                        pong_waiter = await ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=self.heartbeat_timeout)
                    except Exception:
                        dead.append(cid)
                for cid in dead:
                    await self.disconnect(cid)
                    logger.warning("WS heartbeat timeout -> killed: %s", cid)

        self._heartbeat_task = asyncio.create_task(_loop())

    async def stop_heartbeat(self) -> None:
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

    async def disconnect_all(self) -> None:
        async with self._lock:
            for ws in self.active_connections.values():
                try:
                    await ws.close(code=1001, reason="Server shutdown")
                except Exception:
                    pass
            self.active_connections.clear()
        logger.info("WS all connections closed")


# ── Singleton ──
ws_manager = WebSocketConnectionManager()
