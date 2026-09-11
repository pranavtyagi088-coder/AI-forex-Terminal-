from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
FRONTEND = ROOT / "frontend"

api_ts = FRONTEND / "src" / "lib" / "api.ts"
api_test = FRONTEND / "src" / "lib" / "__tests__" / "api.test.ts"
store_test = FRONTEND / "src" / "store" / "__tests__" / "useCockpitStore.test.ts"

print("═══ 1. src/lib/api.ts (First 80 lines) ═══")
if api_ts.exists():
    lines = api_ts.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines[:80], 1):
        print(f"{i:3d}: {line}")

print("\n═══ 2. src/lib/__tests__/api.test.ts (First 40 lines) ═══")
if api_test.exists():
    lines = api_test.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines[:40], 1):
        print(f"{i:3d}: {line}")

print("\n═══ 3. src/store/__tests__/useCockpitStore.test.ts (Lines 110-140) ═══")
if store_test.exists():
    lines = store_test.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines[110:140], 111):
        print(f"{i:3d}: {line}")
