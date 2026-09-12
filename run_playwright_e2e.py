import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
PY_EXEC = BACKEND_DIR / "venv" / "Scripts" / "python.exe"
DEF_BEARER = "dev-secret-token"

def check_url(url, headers=None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            return resp.status in (200, 304)
    except Exception:
        return False

def kill_tree(proc):
    if proc and proc.pid:
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def main():
    print("=" * 64)
    print("INSTITUTIONAL AI TERMINAL - PLAYWRIGHT E2E ORCHESTRATOR")
    print("=" * 64)
    b_proc = None
    f_proc = None
    try:
        b_url = "http://127.0.0.1:8000/api/telemetry/cockpit"
        auth = {"Authorization": f"Bearer {DEF_BEARER}"}
        if not check_url(b_url, auth):
            print("[1/3] Backend (8000) down. Launching Uvicorn...")
            b_proc = subprocess.Popen([str(PY_EXEC), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=str(BACKEND_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(15):
                time.sleep(1)
                if check_url(b_url, auth):
                    print(f"Backend LIVE after {i+1}s.")
                    break
            else:
                print("Backend failed to start.")
                return 1
        else:
            print("[1/3] Backend (8000) ALREADY LIVE.")

        f_url = "http://127.0.0.1:5173"
        if not check_url(f_url):
            print("[2/3] Frontend (5173) down. Launching Vite...")
            f_proc = subprocess.Popen("npx vite --host 127.0.0.1 --port 5173", cwd=str(FRONTEND_DIR), shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for i in range(20):
                time.sleep(1)
                if check_url(f_url):
                    print(f"Frontend LIVE after {i+1}s.")
                    break
            else:
                print("Frontend failed to start.")
                return 1
        else:
            print("[2/3] Frontend (5173) ALREADY LIVE.")

        print("[3/3] Running Playwright E2E Suite...")
        res = subprocess.run("npx playwright test", cwd=str(FRONTEND_DIR), shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(res.stdout)
        if res.stderr:
            print(res.stderr)
        print("=" * 64)
        if res.returncode == 0:
            print("SUCCESS: 4/4 PLAYWRIGHT E2E TESTS GREEN!")
        else:
            print(f"PLAYWRIGHT EXIT CODE: {res.returncode}")
        print("=" * 64)
        return res.returncode
    finally:
        if b_proc:
            print("Cleaning up backend process...")
            kill_tree(b_proc)
        if f_proc:
            print("Cleaning up frontend process...")
            kill_tree(f_proc)

if __name__ == "__main__":
    sys.exit(main())
