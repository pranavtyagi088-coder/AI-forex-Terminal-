from __future__ import annotations

import json
import logging
import asyncio
from typing import Any, Callable, Optional, Dict

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisTelemetryBus:
    """
    Institutional Redis Pub/Sub Telemetry Bridge.
    Fail-safe architecture: does not interrupt core event bus if Redis is unavailable.
    """

    def __init__(self, redis_url: Optional[str] = None, channel: Optional[str] = None, enabled: Optional[bool] = None):
        self.url = redis_url or settings.REDIS_URL or "redis://localhost:6379/0"
        self.channel = channel or settings.REDIS_TELEMETRY_CHANNEL
        self.enabled = enabled if enabled is not None else settings.REDIS_ENABLED
        self._client: Any = None
        self._subscriber_task: Optional[asyncio.Task] = None
        self._is_running = False

    async def connect(self) -> bool:
        """Async connection to Redis server."""
        if not self.enabled:
            return False
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(self.url, decode_responses=True)
            await self._client.ping()
            logger.info("Connected to Redis Pub/Sub at %s", self.url)
            return True
        except Exception as exc:
            logger.warning("Redis connection unavailable (falling back to in-memory bus): %s", exc)
            self._client = None
            return False

    async def publish(self, event_data: Dict[str, Any]) -> bool:
        """Publish event to Redis telemetry channel."""
        if not self.enabled or not self._client:
            return False
        try:
            payload = json.dumps(event_data)
            await self._client.publish(self.channel, payload)
            return True
        except Exception as exc:
            logger.error("Failed to publish to Redis: %s", exc)
            return False

    async def close(self) -> None:
        """Close Redis client connection."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


# Global Singleton Instance
redis_bus = RedisTelemetryBus()
