import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
BACKEND = ROOT / "backend"
PYTHON = BACKEND / "venv" / "Scripts" / "python.exe"

print("===> Launching Uvicorn with live stream output...")
proc = subprocess.Popen(
    [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1"],
    cwd=str(BACKEND),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

connected = False
for i in range(12):
    time.sleep(1)
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/telemetry/cockpit",
            headers={"Authorization": "Bearer dev-secret-token"}
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                print(f"✅ Backend READY in {i+1} seconds! HTTP 200 OK")
                connected = True
                break
    except Exception as e:
        print(f"  [{i+1}s] Waiting for socket bind... ({type(e).__name__})")

proc.terminate()
if not connected:
    print("\n❌ Uvicorn Startup Logs:")
    print(proc.stdout.read())
