import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.engines.telemetry.redis_bus import RedisTelemetryBus

@pytest.mark.asyncio
async def test_redis_bus_disabled_by_default():
    bus = RedisTelemetryBus(enabled=False)
    connected = await bus.connect()
    assert connected is False
    pub_res = await bus.publish({"test": "data"})
    assert pub_res is False

@pytest.mark.asyncio
async def test_redis_bus_connection_failure_fail_safe():
    bus = RedisTelemetryBus(redis_url="redis://127.0.0.1:59999/0", enabled=True)
    connected = await bus.connect()
    assert connected is False
    pub_res = await bus.publish({"event": "TEST"})
    assert pub_res is False

@pytest.mark.asyncio
async def test_redis_bus_successful_publish_mock():
    bus = RedisTelemetryBus(enabled=True)
    mock_client = AsyncMock()
    mock_client.publish = AsyncMock(return_value=1)
    bus._client = mock_client
    
    success = await bus.publish({"event_id": "EVT-001", "msg": "test"})
    assert success is True
    mock_client.publish.assert_awaited_once()
    
    await bus.close()
