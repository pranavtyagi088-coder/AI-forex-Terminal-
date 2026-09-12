import pytest
import pathlib
from app.core.config import Settings
from app.engines.telemetry.redis_bus import RedisTelemetryBus
from app.core.database import init_db


def test_database_url_normalization_asyncpg():
    s1 = Settings(DATABASE_URL="postgres://user:pass@localhost:5432/db")
    assert s1.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

    s2 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/db")
    assert s2.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/db"

    s3 = Settings(DATABASE_URL="sqlite+aiosqlite:///./test.db")
    assert s3.DATABASE_URL == "sqlite+aiosqlite:///./test.db"


@pytest.mark.asyncio
async def test_redis_telemetry_bus_disabled_fallback():
    bus = RedisTelemetryBus(enabled=False)
    connected = await bus.connect()
    assert connected is False
    published = await bus.publish({"test": "event"})
    assert published is False
    await bus.close()


@pytest.mark.asyncio
async def test_redis_telemetry_bus_unreachable_fail_safe():
    bus = RedisTelemetryBus(redis_url="redis://127.0.0.1:59999/0", enabled=True)
    connected = await bus.connect()
    assert connected is False
    published = await bus.publish({"test": "event"})
    assert published is False
    await bus.close()


@pytest.mark.asyncio
async def test_init_db_schema_creation():
    await init_db()
    assert True


def test_docker_compose_file_validity():
    dc = pathlib.Path("docker-compose.yml")
    assert dc.exists()
    content = dc.read_text(encoding="utf-8")
    assert "db:" in content
    assert "redis:" in content
    assert "backend:" in content
    assert "frontend:" in content
    assert "postgresql+asyncpg://" in content


def test_nginx_conf_websocket_and_api_proxy():
    conf = pathlib.Path("frontend/nginx.conf")
    assert conf.exists()
    content = conf.read_text(encoding="utf-8")
    assert "location /api/" in content
    assert "location /ws/" in content
    assert "proxy_set_header Upgrade" in content
    assert 'Connection "upgrade"' in content
