import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
BACKEND = ROOT / "backend"
PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"

print("===> Testing Backend Startup directly with live stdout/stderr...")

# Launch uvicorn and capture logs
proc = subprocess.Popen(
    [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=str(BACKEND),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

time.sleep(3)

# Check if process is still alive
if proc.poll() is not None:
    print(f"\n❌ Uvicorn exited immediately with code {proc.returncode}!")
    print("Logs:")
    print(proc.stdout.read())
else:
    print("✅ Process is alive! Probing endpoint...")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/telemetry/cockpit",
            headers={"Authorization": "Bearer dev-secret-token"}
        )
        with urllib.request.urlopen(req, timeout=3) as resp:
            print(f"✅ Probe HTTP Status: {resp.status}")
            print(f"✅ Response Body Preview: {resp.read()[:200]}")
    except Exception as e:
        print(f"❌ Probe Failed: {e}")
    finally:
        proc.terminate()
