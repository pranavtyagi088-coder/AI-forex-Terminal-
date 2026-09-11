from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
FRONTEND = ROOT / "frontend"
store_ts = FRONTEND / "src" / "store" / "useCockpitStore.ts"
api_test = FRONTEND / "src" / "lib" / "__tests__" / "api.test.ts"

print("═══ 1. useCockpitStore.ts ═══")
if store_ts.exists():
    print(store_ts.read_text(encoding="utf-8"))

print("\n═══ 2. src/lib/__tests__/api.test.ts ═══")
if api_test.exists():
    print(api_test.read_text(encoding="utf-8"))
