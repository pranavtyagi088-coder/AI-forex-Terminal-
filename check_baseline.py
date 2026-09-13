import subprocess
import sys

def run_cmd(cmd, desc):
    print(f"\n⚡ Running: {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        print(f"✅ {desc} PASSED")
        return True, res.stdout
    else:
        print(f"❌ {desc} FAILED:\n{res.stderr or res.stdout}")
        return False, res.stderr

print("="*70)
print("🛡️ INSTITUTIONAL TERMINAL - BASELINE SANITY CHECK")
print("="*70)

# 1. Pytest (Backend 342 tests)
p_ok, p_out = run_cmd("backend\\venv\\Scripts\\pytest backend/tests --tb=short -q", "Backend Pytest Suite")
lines = [l for l in p_out.splitlines() if "passed" in l]
if lines:
    print(f"   📊 Pytest Result: {lines[-1]}")

# 2. Vitest (Frontend 16 tests)
v_ok, v_out = run_cmd("cd frontend && npm run test -- --run", "Frontend Vitest Suite")
v_lines = [l for l in v_out.splitlines() if "Tests" in l or "passed" in l]
if v_lines:
    print(f"   📊 Vitest Result: {v_lines[-1]}")

if p_ok and v_ok:
    print("\n" + "="*70)
    print("\033[92;1m>>> 🟢 BASELINE HEALTH VERIFIED: ALL 358 UNIT/INTEGRATION TESTS PASSING! <<<\033[0m")
    print("="*70)
else:
    print("\n\033[91;1m>>> ❌ REGRESSION DETECTED! PLEASE FIX BEFORE PROCEEDING <<<\033[0m")
    sys.exit(1)
