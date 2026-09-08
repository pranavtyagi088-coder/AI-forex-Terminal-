import asyncio
import os
import pytest
from app.core.database import init_db
from app.engines.risk.circuit_breaker import CircuitBreakerEngine, _BREAKER_STATE_FILE
from app.engines.risk import gatekeeper as gk_module

@pytest.fixture(scope="session", autouse=True)
def setup_test_database_session():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()

@pytest.fixture(autouse=True)
def reset_circuit_breaker():
    def _do_reset():
        # 1. Reset via engine instance
        cb = CircuitBreakerEngine()
        try:
            cb.manual_reset(admin_confirmed=True)
        except Exception:
            pass

        # 2. Reset module-level singleton if exists in gatekeeper
        if hasattr(gk_module, "breaker_engine"):
            try:
                gk_module.breaker_engine.manual_reset(admin_confirmed=True)
            except Exception:
                pass
        if hasattr(gk_module, "_circuit_breaker"):
            try:
                gk_module._circuit_breaker.manual_reset(admin_confirmed=True)
            except Exception:
                pass

        # 3. Clean physical state file
        if os.path.exists(_BREAKER_STATE_FILE):
            try:
                os.remove(_BREAKER_STATE_FILE)
            except Exception:
                pass

    _do_reset()
    yield
    _do_reset()

@pytest.fixture
def auth_headers():
    from app.core.config import settings
    return {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
