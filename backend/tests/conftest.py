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






@pytest.fixture(autouse=True)
def _reset_circuit_breaker_isolation():
    """Ensure persistent disk kill-switch is reset safely for clean test isolation."""
    import os, glob
    for f in glob.glob("**/circuit_breaker*.json", recursive=True):
        try: os.remove(f)
        except Exception: pass

    try:
        from app.engines.risk.circuit_breaker import CircuitBreakerEngine
        cb = CircuitBreakerEngine()
        for method_name in ["reset_circuit_breaker", "reset_breaker", "reset_state", "reset"]:
            if hasattr(cb, method_name):
                getattr(cb, method_name)("Pytest Isolation Reset")
                break
    except Exception:
        pass

    yield

    for f in glob.glob("**/circuit_breaker*.json", recursive=True):
        try: os.remove(f)
        except Exception: pass

