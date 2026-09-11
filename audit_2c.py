from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

files_to_inspect = [
    ("Confluence Engine", BACKEND / "app" / "engines" / "intelligence" / "confluence.py"),
    ("Telemetry Hub", BACKEND / "app" / "engines" / "telemetry" / "hub.py"),
    ("Cockpit Route", BACKEND / "app" / "api" / "routes" / "telemetry.py"),
]

for label, fpath in files_to_inspect:
    print(f"\n{'='*70}")
    print(f"  {label}: {fpath.relative_to(BACKEND)}")
    print(f"{'='*70}")
    if fpath.exists():
        content = fpath.read_text(encoding="utf-8")
        lines = content.splitlines()
        print(f"  Total lines: {len(lines)}")
        print(f"  Size: {fpath.stat().st_size} bytes")
        print(f"\n  --- First 60 lines ---")
        for i, line in enumerate(lines[:60], 1):
            print(f"  {i:3d}: {line}")
        if len(lines) > 60:
            print(f"\n  --- Lines 60-120 ---")
            for i, line in enumerate(lines[60:120], 61):
                print(f"  {i:3d}: {line}")
    else:
        print(f"  ❌ FILE NOT FOUND")

# Also check cockpit payload schema
print(f"\n{'='*70}")
print("  Searching for CockpitTelemetryPayload definition...")
print(f"{'='*70}")
for py_file in BACKEND.rglob("*.py"):
    content = py_file.read_text(encoding="utf-8", errors="ignore")
    if "CockpitTelemetryPayload" in content and "class" in content:
        rel = py_file.relative_to(BACKEND)
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "class CockpitTelemetryPayload" in line:
                print(f"\n  Found in {rel} at line {i+1}:")
                for j in range(i, min(i+40, len(lines))):
                    print(f"  {j+1:3d}: {lines[j]}")
                break

# Check frontend cockpit components
print(f"\n{'='*70}")
print("  Frontend Cockpit Components:")
print(f"{'='*70}")
cockpit_dir = FRONTEND / "src" / "components" / "cockpit"
if cockpit_dir.exists():
    for f in cockpit_dir.rglob("*.{ts,tsx}"):
        rel = f.relative_to(FRONTEND)
        print(f"  • {rel} ({f.stat().st_size} bytes)")

# Check telemetry types
types_file = FRONTEND / "src" / "types" / "telemetry.ts"
if types_file.exists():
    print(f"\n{'='*70}")
    print("  Frontend Telemetry Types:")
    print(f"{'='*70}")
    print(types_file.read_text(encoding="utf-8"))
