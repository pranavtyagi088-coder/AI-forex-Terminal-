from pathlib import Path
import re

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")
print("=" * 75)
print(" AUDIT: OPTION D - BROKER COCKPIT FRONTEND PANEL")
print("=" * 75)

# ---- 1. Backend Broker API surface ----
trades_route = ROOT / "backend" / "app" / "api" / "routes" / "trades.py"
print(f"\n[1] BACKEND: trades.py  EXISTS={trades_route.exists()}")
if trades_route.exists():
    src = trades_route.read_text(encoding="utf-8-sig", errors="replace")
    routes = re.findall(r'@router\.(get|post|delete|put)\(\s*["\']([^"\']+)["\']', src)
    broker_routes = [(m, p) for m, p in routes if "broker" in p.lower() or "proposal" in p.lower()]
    print(f"    Broker/Proposal routes found: {len(broker_routes)}")
    for m, p in broker_routes:
        print(f"      {m.upper():6s} {p}")

# ---- 2. Broker Bridge + Adapter files ----
for f in ["backend/app/services/broker/base.py",
          "backend/app/services/broker/mt5_adapter.py",
          "backend/app/services/broker/bridge.py",
          "backend/app/engines/execution/events.py"]:
    p = ROOT / f
    sz = p.stat().st_size if p.exists() else 0
    print(f"\n[2] {f}  EXISTS={p.exists()}  SIZE={sz}")

# ---- 3. Frontend cockpit inventory ----
cockpit_dir = ROOT / "frontend" / "src" / "components" / "cockpit"
print(f"\n[3] FRONTEND cockpit dir: EXISTS={cockpit_dir.exists()}")
if cockpit_dir.exists():
    for f in sorted(cockpit_dir.glob("*.tsx")):
        print(f"      {f.name:35s} {f.stat().st_size} bytes")

# ---- 4. api.ts client contract ----
api_ts = ROOT / "frontend" / "src" / "lib" / "api.ts"
print(f"\n[4] FRONTEND api.ts EXISTS={api_ts.exists()}")
if api_ts.exists():
    src = api_ts.read_text(encoding="utf-8-sig", errors="replace")
    exports = re.findall(r'export\s+(?:async\s+)?function\s+(\w+)', src)
    print(f"    Exported functions: {len(exports)}")
    for fn in exports:
        is_broker = "broker" in fn.lower() or "proposal" in fn.lower()
        marker = "  <-- BROKER" if is_broker else ""
        print(f"      {fn}{marker}")

# ---- 5. Zustand store ----
store_dir = ROOT / "frontend" / "src" / "store"
print(f"\n[5] FRONTEND store dir: EXISTS={store_dir.exists()}")
if store_dir.exists():
    for f in sorted(store_dir.glob("*.ts")):
        print(f"      {f.name}")

# ---- 6. App.tsx mount points ----
app_tsx = ROOT / "frontend" / "src" / "App.tsx"
print(f"\n[6] FRONTEND App.tsx EXISTS={app_tsx.exists()}")
if app_tsx.exists():
    src = app_tsx.read_text(encoding="utf-8-sig", errors="replace")
    imports = re.findall(r'from\s+["\']\./components/cockpit/(\w+)["\']', src)
    print(f"    Cockpit panel imports: {imports}")

# ---- 7. Types dir ----
types_dir = ROOT / "frontend" / "src" / "types"
print(f"\n[7] FRONTEND types dir: EXISTS={types_dir.exists()}")
if types_dir.exists():
    for f in sorted(types_dir.glob("*.ts")):
        print(f"      {f.name}")

print("\n" + "=" * 75)
print(" AUDIT READY")
print("=" * 75)
