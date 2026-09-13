import subprocess
import sys
from pathlib import Path

print("="*75)
print("🚀 COMMITTING & PUSHING PHASE TO GITHUB")
print("="*75)

# Clean up temporary check scripts
temp_files = [
    "check_baseline.py", 
    "audit_broker_ui.py", 
    "deep_audit_broker.py", 
    "final_audit_broker.py", 
    "verify_live_endpoints.py", 
    "verify_endpoints_stdlib.py", 
    "run_playwright.py", 
    "run_playwright_fixed.py"
]
for f in temp_files:
    p = Path(f)
    if p.exists():
        p.unlink()
        print(f"🧹 Cleaned up temporary script: {f}")

# Git Status
subprocess.run(["git", "status", "--short"])

# Git Add
subprocess.run(["git", "add", "."])

# Git Commit
msg = "feat(cockpit): verify & solidify institutional broker bridge UI & E2E suite (370/370 tests green)"
res = subprocess.run(["git", "commit", "-m", msg], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(res.stdout or res.stderr)

# Git Push
push_res = subprocess.run(["git", "push"], capture_output=True, text=True, encoding="utf-8", errors="replace")
print(push_res.stdout or push_res.stderr)

if push_res.returncode == 0:
    print("\033[92;1m>>> GIT COMMIT & PUSH COMPLETED SUCCESSFULLY <<<\033[0m")
else:
    print("\033[93;1m>>> ⚠️ Git Push Note: Check if remote is configured or up-to-date <<<\033[0m")
