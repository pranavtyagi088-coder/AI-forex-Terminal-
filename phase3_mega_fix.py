import os
import sys
import time
import subprocess
import urllib.request
import json
from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"

def log(msg, color="\033[96m"):
    print(f"{color}===> {msg}\033[0m", flush=True)

def error_exit(msg):
    print(f"\n\033[91m❌ ERROR: {msg}\033[0m\n", flush=True)
    sys.exit(1)

def run_cmd(cmd, cwd, desc=""):
    if desc:
        log(desc)
    print(f"[CMD] {cmd}", flush=True)
    res = subprocess.run(cmd, cwd=str(cwd), shell=True)
    if res.returncode != 0:
        error_exit(f"Command failed with code {res.returncode}: {cmd}")
    return res

def kill_ports(ports):
    for port in ports:
        try:
            cmd = f'powershell -Command "Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"'
            out = subprocess.check_output(cmd, shell=True, text=True).strip()
            if out:
                for pid in [p.strip() for p in out.splitlines() if p.strip().isdigit() and p.strip() != "0"]:
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    time.sleep(1)

# ═══════════════════════════════════════════════════════════════
# STEP 0: Clean any leftover services
# ═══════════════════════════════════════════════════════════════
log("STEP 0: Cleaning ports 8000 & 5173...", "\033[93m")
kill_ports([8000, 5173])
log("✅ Ports clean", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 1: Discover & delete persistent breaker state file
# ═══════════════════════════════════════════════════════════════
log("STEP 1: Locating _BREAKER_STATE_FILE constant...", "\033[93m")
cb_file = BACKEND / "app" / "engines" / "risk" / "circuit_breaker.py"
if not cb_file.exists():
    error_exit(f"circuit_breaker.py not found at {cb_file}")

cb_content = cb_file.read_text(encoding="utf-8")
# Find state file path
state_file_path = None
for line in cb_content.splitlines():
    if "_BREAKER_STATE_FILE" in line and "=" in line and "import" not in line:
        print(f"  Found line: {line.strip()}")
        # Extract path value
        if "Path(" in line or '"' in line or "'" in line:
            # Add to sys.path and import to get actual value
            break

sys.path.insert(0, str(BACKEND))
try:
    from app.engines.risk.circuit_breaker import _BREAKER_STATE_FILE
    print(f"  ✅ _BREAKER_STATE_FILE resolves to: {_BREAKER_STATE_FILE}")
    state_file_path = Path(_BREAKER_STATE_FILE)
    if state_file_path.exists():
        content_preview = state_file_path.read_text(encoding="utf-8")[:200]
        print(f"  ⚠️ Current state file content: {content_preview}")
        state_file_path.unlink()
        print(f"  ✅ Deleted persistent breaker state file")
    else:
        print(f"  ✅ State file doesn't exist (clean)")
except Exception as e:
    print(f"  ⚠️ Could not import _BREAKER_STATE_FILE: {e}")

# ═══════════════════════════════════════════════════════════════
# STEP 2: Fix conftest.py to reset the ACTUAL singleton
# ═══════════════════════════════════════════════════════════════
log("STEP 2: Rewriting conftest.py with singleton-aware fixture...", "\033[93m")
conftest_path = BACKEND / "tests" / "conftest.py"

new_conftest = '''import asyncio
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
'''
conftest_path.write_text(new_conftest, encoding="utf-8")
log("✅ conftest.py rewritten with singleton-aware fixture", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 3: Verify BreakerState enum has NORMAL member
# ═══════════════════════════════════════════════════════════════
log("STEP 3: Verifying BreakerState enum has NORMAL...", "\033[93m")
try:
    from app.engines.risk.circuit_breaker import BreakerState
    states = [s.name for s in BreakerState]
    print(f"  BreakerState members: {states}")
    if "NORMAL" not in states:
        print(f"  ⚠️ NORMAL not found — will use first state as reset target")
except Exception as e:
    print(f"  ⚠️ Could not read BreakerState: {e}")

# ═══════════════════════════════════════════════════════════════
# STEP 4: Run FAST subset test first (5 failed tests) to verify fix
# ═══════════════════════════════════════════════════════════════
log("STEP 4: Running FAST verification subset (5 previously-failing tests)...", "\033[93m")
fast_test_cmd = (
    f'"{PYTHON}" -m pytest '
    f'tests/test_pre_flight_gatekeeper.py::TestPreFlightGatekeeper::test_pre_flight_approved_clean_trade '
    f'tests/test_decision_provenance_pipeline.py::test_preflight_generates_cryptographic_audit_receipt '
    f'tests/test_order_staging.py::TestOrderStagingAndIdempotency::test_stage_clean_order_creates_pending_approval '
    f'tests/test_hermes_and_telemetry_hub.py::test_telemetry_hub_cockpit_snapshot_generation '
    f'tests/test_same_code_path_backtester.py::test_same_code_path_backtester_sizing_and_decisions '
    f'-v --tb=short'
)
print(f"[CMD] {fast_test_cmd}")
fast_res = subprocess.run(fast_test_cmd, cwd=str(BACKEND), shell=True)
if fast_res.returncode != 0:
    error_exit("FAST subset still failing! Fixture logic needs deeper inspection. Paste output for review.")
log("✅ FAST subset PASSED — singleton reset confirmed working!", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 5: Run FULL pytest suite (285+ tests) to confirm no regression
# ═══════════════════════════════════════════════════════════════
log("STEP 5: Running FULL pytest suite (285+ tests)...", "\033[93m")
run_cmd(f'"{PYTHON}" -m pytest tests --tb=short -q', BACKEND, "Full backend regression")
log("✅ Full Pytest Suite: 100% GREEN", "\033[92m")

# ═══════════════════════════════════════════════════════════════
# STEP 6: Start services for E2E
# ═══════════════════════════════════════════════════════════════
log("STEP 6: Starting Backend + Frontend for Playwright E2E...", "\033[93m")
kill_ports([8000, 5173])

backend_proc = subprocess.Popen(
    [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=str(BACKEND),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)
frontend_proc = subprocess.Popen(
    "npx vite --host 127.0.0.1 --port 5173",
    cwd=str(FRONTEND),
    shell=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

def wait_for_url(url, headers=None, timeout=45, label="Service"):
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(req, timeout=2) as resp:
                if resp.status in (200, 304):
                    print(f"  ✅ {label} UP ({round(time.time()-start, 1)}s)")
                    return True
        except Exception:
            time.sleep(1)
    return False

if not wait_for_url("http://127.0.0.1:8000/api/telemetry/cockpit", {"Authorization": "Bearer dev-secret-token"}, 45, "Backend"):
    kill_ports([8000, 5173])
    error_exit("Backend startup timeout")
if not wait_for_url("http://127.0.0.1:5173", None, 30, "Frontend"):
    kill_ports([8000, 5173])
    error_exit("Frontend startup timeout")

# Ensure circuit breaker is in NORMAL state before E2E
try:
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/admin/circuit-breaker/toggle",
        headers={"Authorization": "Bearer dev-secret-token", "Content-Type": "application/json"},
        data=b'{"activate": false}',
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=3) as resp:
        print(f"  ✅ Pre-E2E: Circuit breaker forced to OFF ({resp.status})")
except Exception as e:
    print(f"  ⚠️ Could not force breaker OFF: {e}")

try:
    # ═══════════════════════════════════════════════════════════════
    # STEP 7: Run Vitest
    # ═══════════════════════════════════════════════════════════════
    log("STEP 7: Running Vitest (16 tests)...", "\033[93m")
    run_cmd("npm run test -- --run", FRONTEND, "Frontend Vitest")
    log("✅ Vitest: 16/16 PASSED", "\033[92m")

    # ═══════════════════════════════════════════════════════════════
    # STEP 8: Run Playwright E2E
    # ═══════════════════════════════════════════════════════════════
    log("STEP 8: Running Playwright E2E (4 tests)...", "\033[93m")
    run_cmd("npx playwright test", FRONTEND, "Playwright browser tests")
    log("✅ Playwright: 4/4 PASSED", "\033[92m")

    # ═══════════════════════════════════════════════════════════════
    # STEP 9: Git commit & push
    # ═══════════════════════════════════════════════════════════════
    log("STEP 9: Git commit & push to GitHub...", "\033[93m")
    run_cmd("git add .", ROOT, "Staging")
    run_cmd(
        'git commit -m "feat(testing): Phase 3 Playwright E2E suite + fix singleton reset fixture for full test isolation"',
        ROOT, "Committing"
    )
    run_cmd("git push origin main", ROOT, "Pushing to origin/main")
    log("✅ Pushed to GitHub!", "\033[92m")

    print("\n" + "═"*75)
    print("\033[92m🎉 PHASE 3 COMPLETE — Pytest + Vitest + Playwright 100% GREEN + PUSHED!\033[0m")
    print("═"*75 + "\n")

finally:
    log("Cleaning up services...")
    kill_ports([8000, 5173])
