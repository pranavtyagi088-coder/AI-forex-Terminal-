from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def dump(label, path, max_lines=None):
    print("\n" + "=" * 78)
    print(f" {label}")
    print(f" PATH: {path}")
    print("=" * 78)
    p = ROOT / path
    if not p.exists():
        print(" [MISSING]")
        return
    text = p.read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    if max_lines:
        for i, line in enumerate(lines[:max_lines], 1):
            print(f"{i:4d} | {line}")
        if len(lines) > max_lines:
            print(f"     | ... ({len(lines) - max_lines} more lines)")
    else:
        for i, line in enumerate(lines, 1):
            print(f"{i:4d} | {line}")

# Backend schemas we need to mirror in TS
dump("BACKEND: broker/base.py (dataclasses)", "backend/app/services/broker/base.py")
dump("BACKEND: broker/bridge.py (return types)", "backend/app/services/broker/bridge.py")
dump("BACKEND: execution/events.py", "backend/app/engines/execution/events.py")

# Backend route bodies - so we know exact response shapes
dump("BACKEND: trades.py (route handlers)", "backend/app/api/routes/trades.py")

# Frontend existing patterns
dump("FRONTEND: api.ts (current)", "frontend/src/lib/api.ts")
dump("FRONTEND: types/telemetry.ts", "frontend/src/types/telemetry.ts")
dump("FRONTEND: store/useCockpitStore.ts", "frontend/src/store/useCockpitStore.ts")
dump("FRONTEND: App.tsx", "frontend/src/App.tsx")

# One reference panel for style matching
dump("FRONTEND: ZoneRadarPanel.tsx (style reference)", "frontend/src/components/cockpit/ZoneRadarPanel.tsx")

# One test file for test-style matching
tests = list((ROOT / "frontend" / "src").rglob("*.test.tsx"))
print(f"\n\n[TEST FILES FOUND] {len(tests)}")
for t in tests:
    print(f"  - {t.relative_to(ROOT)}")
if tests:
    dump(f"FRONTEND: {tests[0].name} (test style reference)", str(tests[0].relative_to(ROOT)).replace("\\\\", "/"))

# WS hook (if exists) for event integration
for candidate in ["frontend/src/hooks/useTelemetryStream.ts",
                  "frontend/src/hooks/useCockpitStream.ts",
                  "frontend/src/lib/ws.ts"]:
    p = ROOT / candidate
    if p.exists():
        dump(f"FRONTEND WS: {candidate}", candidate)

print("\n" + "=" * 78)
print(" DEEP INSPECTION COMPLETE")
print("=" * 78)
