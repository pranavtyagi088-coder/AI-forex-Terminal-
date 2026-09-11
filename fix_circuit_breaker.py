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
# STEP 1: Find circuit breaker module & understand its API
# ═══════════════════════════════════════════════════════════════
log("STEP 1: Locating global_circuit_breaker singleton...", "\033[93m")

# Search for the circuit breaker definition
search_cmd = f'powershell -Command "Get-ChildItem -Path \'{BACKEND}\\app\' -Recurse -Filter \'*.py\' | Select-String -Pattern \'global_circuit_breaker|class.*CircuitBreaker|circuit_breaker.*=.*\' | Select-Object -First 20 Path,LineNumber,Line"'
result = subprocess.run(search_cmd, shell=True, capture_output=True, text=True)
print("Search results:")
print(result.stdout[:2000] if result.stdout else "(no output)")

# Also search in tests/conftest.py
conftest_path = BACKEND / "tests" / "conftest.py"
print(f"\nconftest.py exists: {conftest_path.exists()}")
if conftest_path.exists():
    print(f"conftest.py content:\n{conftest_path.read_text(encoding='utf-8')[:1000]}")

# Find the exact import path for circuit breaker
grep_cmd = f'powershell -Command "Get-ChildItem -Path \'{BACKEND}\\app\' -Recurse -Filter \'*.py\' | Select-String -Pattern \'global_circuit_breaker\' | Select-Object Path,Line"'
grep_result = subprocess.run(grep_cmd, shell=True, capture_output=True, text=True)
print(f"\nAll global_circuit_breaker references:\n{grep_result.stdout[:3000]}")

# ═══════════════════════════════════════════════════════════════
# STEP 2: Read gatekeeper.py to understand reset mechanism
# ═══════════════════════════════════════════════════════════════
log("STEP 2: Reading gatekeeper module for reset API...", "\033[93m")

# Try common paths
possible_paths = [
    BACKEND / "app" / "engines" / "risk" / "gatekeeper.py",
    BACKEND / "app" / "core" / "gatekeeper.py",
    BACKEND / "app" / "gatekeeper.py",
    BACKEND / "app" / "engines" / "gatekeeper.py",
]

gatekeeper_path = None
for p in possible_paths:
    if p.exists():
        gatekeeper_path = p
        break

if not gatekeeper_path:
    # Search for it
    find_cmd = f'powershell -Command "Get-ChildItem -Path \'{BACKEND}\\app\' -Recurse -Filter \'gatekeeper.py\' | Select-Object -ExpandProperty FullName"'
    find_result = subprocess.run(find_cmd, shell=True, capture_output=True, text=True)
    found = find_result.stdout.strip()
    if found:
        gatekeeper_path = Path(found.splitlines()[0])

if gatekeeper_path and gatekeeper_path.exists():
    content = gatekeeper_path.read_text(encoding="utf-8")
    print(f"Found gatekeeper at: {gatekeeper_path}")
    # Print first 80 lines to understand the class
    lines = content.splitlines()[:80]
    for i, line in enumerate(lines, 1):
        print(f"  {i:3d}: {line}")
else:
    print("⚠️ gatekeeper.py not found at common paths, searching broadly...")
    find_all = f'powershell -Command "Get-ChildItem -Path \'{BACKEND}\' -Recurse -Filter \'*.py\' | Select-String -Pattern \'class.*CircuitBreaker|def.*reset|def.*disable|def.*toggle\' | Select-Object Path,Line"'
    r = subprocess.run(find_all, shell=True, capture_output=True, text=True)
    print(r.stdout[:2000])

print("\n" + "="*70)
print("DIAGNOSTIC COMPLETE — Paste this output back for surgical fix!")
print("="*70)
