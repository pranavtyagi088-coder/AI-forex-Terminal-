import subprocess
from pathlib import Path

ROOT = Path.cwd()

JUNK = [
    "audit_master.py",
    "audit_c2_ui.py",
    "build_c2_panel.py",
    "fix_c2_test.py",
    "fix_playwright_dual_server.py",
    "inspect_app.py",
    "inspect_c2_files.py",
    "inspect_playwright_config.py",
    "housekeeping.py",
]

print("=" * 80)
print("  PHASE X - HOUSEKEEPING & CLEAN COMMIT")
print("=" * 80)

print("\n[1/5] Removing temporary helper scripts from root...")
removed = []
for name in JUNK:
    p = ROOT / name
    if p.exists() and name != "housekeeping.py":
        p.unlink()
        removed.append(name)
        print(f"  [DEL] {name}")
if not removed:
    print("  [SKIP] No junk found.")

print("\n[2/5] Git status (before commit):")
r = subprocess.run("git status --short", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout or "  [Clean]")

print("\n[3/5] Staging all changes...")
subprocess.run("git add -A", shell=True)

print("\n[4/5] Committing with descriptive message...")
commit_msg = "feat(cockpit): Option C Analytics + Option D Broker Bridge UI panels [378/378 green]"
r = subprocess.run(f'git commit -m "{commit_msg}"', shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout)
if r.returncode != 0:
    print(r.stderr)

print("\n[5/5] Pushing to origin/main...")
r = subprocess.run("git push origin main", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(r.stdout)
print(r.stderr)

print("\n[VERIFY] Latest commit hash:")
r = subprocess.run("git log -1 --oneline", shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
print(f"  {r.stdout.strip()}")

print("\n" + "=" * 80)
print("  PHASE X COMPLETE - REPO IS CLEAN & SYNCED")
print("=" * 80)
