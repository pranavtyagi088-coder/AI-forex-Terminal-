"""
WebSocket Telemetry Test Suite — Institutional Grade.
Tests: Auth gate, connect/disconnect, broadcast, ping/pong, status, cleanup.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.engines.telemetry.ws_manager import WebSocketConnectionManager


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def valid_token():
    return settings.API_AUTH_TOKEN


# ── AUTH GATE TESTS ──

class TestWSAuthGate:
    def test_ws_rejects_missing_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/telemetry"):
                pass

    def test_ws_rejects_invalid_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/telemetry?token=wrong_token"):
                pass

    def test_ws_rejects_empty_token(self, client):
        with pytest.raises(Exception):
            with client.websocket_connect("/ws/telemetry?token="):
                pass

    def test_ws_accepts_valid_token(self, client, valid_token):
        with client.websocket_connect(f"/ws/telemetry?token={valid_token}") as ws:
            data = ws.receive_json()
            assert data["type"] == "SYSTEM"
            assert data["severity"] == "INFO"
            assert "client_id" in data
            assert data["active_connections"] >= 1


# ── PING / PONG TESTS ──

class TestWSPingPong:
    def test_ping_returns_pong(self, client, valid_token):
        with client.websocket_connect(f"/ws/telemetry?token={valid_token}") as ws:
            ws.receive_json()  # consume welcome
            ws.send_text("ping")
            pong = ws.receive_json()
            assert pong["type"] == "PONG"
            assert "timestamp" in pong
            assert "client_id" in pong


# ── STATUS COMMAND TESTS ──

class TestWSStatus:
    def test_status_returns_active_count(self, client, valid_token):
        with client.websocket_connect(f"/ws/telemetry?token={valid_token}") as ws:
            ws.receive_json()  # consume welcome
            ws.send_text("status")
            status = ws.receive_json()
            assert status["type"] == "STATUS"
            assert status["active_connections"] >= 1
            assert "all_clients" in status


# ── UNKNOWN COMMAND TESTS ──

class TestWSUnknownCommand:
    def test_unknown_command_returns_error(self, client, valid_token):
        with client.websocket_connect(f"/ws/telemetry?token={valid_token}") as ws:
            ws.receive_json()  # consume welcome
            ws.send_text("foobar_garbage")
            err = ws.receive_json()
            assert err["type"] == "ERROR"
            assert "Unknown command" in err["message"]


# ── CONNECTION MANAGER UNIT TESTS ──

class TestWSConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        mock_ws = AsyncMock()
        await mgr.connect(mock_ws, "test_client_1")
        assert mgr.get_active_count() == 1
        assert "test_client_1" in mgr.get_client_ids()
        await mgr.disconnect("test_client_1")
        assert mgr.get_active_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_delivers_to_all(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await mgr.connect(ws1, "c1")
        await mgr.connect(ws2, "c2")
        delivered = await mgr.broadcast({"type": "TEST", "msg": "hello"})
        assert delivered == 2
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_cleans_dead_connections(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_json.side_effect = Exception("dead")
        await mgr.connect(ws_alive, "alive")
        await mgr.connect(ws_dead, "dead")
        delivered = await mgr.broadcast({"type": "TEST"})
        assert delivered == 1
        assert mgr.get_active_count() == 1
        assert "alive" in mgr.get_client_ids()

    @pytest.mark.asyncio
    async def test_duplicate_client_replaces_old(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        ws_old = AsyncMock()
        ws_new = AsyncMock()
        await mgr.connect(ws_old, "dup_client")
        await mgr.connect(ws_new, "dup_client")
        assert mgr.get_active_count() == 1
        ws_old.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_success(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        ws = AsyncMock()
        await mgr.connect(ws, "target")
        result = await mgr.send_personal("target", {"type": "DIRECT"})
        assert result is True
        ws.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_personal_missing_client(self):
        mgr = WebSocketConnectionManager()
        result = await mgr.send_personal("ghost", {"type": "DIRECT"})
        assert result is False

    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        mgr = WebSocketConnectionManager()
        from unittest.mock import AsyncMock
        for i in range(5):
            await mgr.connect(AsyncMock(), f"c{i}")
        assert mgr.get_active_count() == 5
        await mgr.disconnect_all()
        assert mgr.get_active_count() == 0


# ── EVENT BUS SUBSCRIBER TESTS ──

class TestEventBusSubscriber:
    def test_register_and_unregister_subscriber(self):
        from app.engines.events.bus import EventBus
        bus = EventBus()
        async def dummy_sub(event): pass
        bus.register_subscriber(dummy_sub)
        assert bus.subscriber_count == 1
        bus.unregister_subscriber(dummy_sub)
        assert bus.subscriber_count == 0

    def test_duplicate_subscriber_ignored(self):
        from app.engines.events.bus import EventBus
        bus = EventBus()
        async def dummy_sub(event): pass
        bus.register_subscriber(dummy_sub)
        bus.register_subscriber(dummy_sub)
        assert bus.subscriber_count == 1
