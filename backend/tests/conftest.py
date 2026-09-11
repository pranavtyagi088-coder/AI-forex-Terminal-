import asyncio
import os
import pytest
from pathlib import Path

from app.core.database import init_db
from app.engines.risk.circuit_breaker import (
    global_circuit_breaker,
    BreakerState,
    _BREAKER_STATE_FILE,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database_session():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(init_db())
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def reset_global_circuit_breaker_singleton():
    """
    Institutional Fix: Resets the ACTUAL module-level singleton before every test.
    Previous fixture created a NEW instance which never touched the real singleton
    used by gatekeeper.py, hub.py, and routes/admin.py. This caused persistent
    KILL_SWITCH state to leak across tests after P1-04 E2E toggle scenarios.
    """
    # 1. Delete persistent state file (prevents disk-based state leak)
    try:
        state_path = Path(_BREAKER_STATE_FILE)
        if state_path.exists():
            state_path.unlink()
    except Exception:
        pass

    # 2. Reset the actual singleton in-memory
    try:
        global_circuit_breaker.manual_reset(admin_confirmed=True)
    except Exception:
        # If already in NORMAL state, manual_reset may be a no-op
        pass

    # 3. Force state attribute directly as belt-and-braces safety
    try:
        if hasattr(global_circuit_breaker, "state"):
            global_circuit_breaker.state = BreakerState.NORMAL
        if hasattr(global_circuit_breaker, "_state"):
            global_circuit_breaker._state = BreakerState.NORMAL
    except Exception:
        pass

    yield

    # Cleanup after test - ensure no test leaves the singleton in KILL_SWITCH
    try:
        global_circuit_breaker.manual_reset(admin_confirmed=True)
    except Exception:
        pass
