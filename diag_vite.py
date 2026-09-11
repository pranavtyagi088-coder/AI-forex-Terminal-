import subprocess
import time
import urllib.request
from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
FRONTEND = ROOT / "frontend"

print("===> Launching Vite dev server and reading live output...")
proc = subprocess.Popen(
    "npm run dev",
    cwd=str(FRONTEND),
    shell=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

for _ in range(8):
    time.sleep(1)
    # Check if process died
    if proc.poll() is not None:
        print(f"❌ Vite exited with code {proc.returncode}")
        break

# Read whatever output Vite printed
proc.terminate()
try:
    stdout, _ = proc.communicate(timeout=2)
    print("--- VITE OUTPUT ---")
    print(stdout)
    print("-------------------")
except Exception as e:
    print(f"Error reading stdout: {e}")
