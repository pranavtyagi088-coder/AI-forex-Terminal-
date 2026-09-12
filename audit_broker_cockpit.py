from pathlib import Path

ROOT = Path(r"C:\Users\PRANAV TYAGI\PycharmProjects\WelcomeScreen")

def section(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def read_safe(path):
    p = ROOT / path
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8-sig", errors="replace")

# ===== 1. BACKEND: trades.py broker endpoints =====
section("1. BACKEND ROUTES: trades.py")
text = read_safe("backend/app/api/routes/trades.py")
if text:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "@router." in line and any(k in line.lower() for k in ["broker", "propos", "approve", "pre-flight"]):
            print(f"\n L{idx+1}: {line.strip()}")
            for j in range(idx+1, min(idx+5, len(lines))):
                print(f"      {lines[j].strip()}")

# ===== 2. BACKEND: bridge.py & mt5_adapter interface =====
section("2. BACKEND: BrokerBridge + Adapter public methods")
for f in ["backend/app/services/broker/bridge.py",
          "backend/app/services/broker/mt5_adapter.py",
          "backend/app/services/broker/base.py"]:
    text = read_safe(f)
    if text:
        print(f"\n[FILE] {f}")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("class ") or s.startswith("async def ") or s.startswith("def "):
                print(f"    {s}")

# ===== 3. FRONTEND: api.ts current endpoints =====
section("3. FRONTEND: services/api.ts")
text = read_safe("frontend/src/services/api.ts")
if text:
    lines = text.splitlines()
    for idx, line in enumerate(lines):
        if "export" in line and ("function" in line or "const" in line or "interface" in line or "type" in line):
            print(f"    L{idx+1}: {line.strip()[:110]}")

# ===== 4. FRONTEND: cockpitStore.ts state slices =====
section("4. FRONTEND: store/cockpitStore.ts")
text = read_safe("frontend/src/store/cockpitStore.ts")
if text:
    lines = text.splitlines()
    for idx, line in enumerate(lines[:120]):
        s = line.strip()
        if s.startswith("interface ") or s.startswith("type ") or "broker" in s.lower() or "proposal" in s.lower():
            print(f"    L{idx+1}: {s}")

# ===== 5. FRONTEND: cockpit panels directory =====
section("5. FRONTEND: components/cockpit/*.tsx")
panels_dir = ROOT / "frontend/src/components/cockpit"
if panels_dir.exists():
    for p in sorted(panels_dir.glob("*.tsx")):
        size_kb = p.stat().st_size / 1024
        print(f"    {p.name:<45} ({size_kb:.1f} KB)")

# ===== 6. DUPLICATE CHECK: BrokerBridgePanel =====
section("6. DUPLICATE CHECK: BrokerBridgePanel")
candidates = [
    "frontend/src/components/cockpit/BrokerBridgePanel.tsx",
    "frontend/src/components/cockpit/BrokerPanel.tsx",
    "frontend/src/components/cockpit/ApprovalQueuePanel.tsx",
]
for c in candidates:
    exists = (ROOT / c).exists()
    tag = "EXISTS" if exists else "MISSING"
    print(f"    [{tag}] {c}")

# ===== 7. Existing tests =====
section("7. TESTS: existing frontend tests")
test_dir = ROOT / "frontend/src"
for p in test_dir.rglob("*.test.tsx"):
    print(f"    {p.relative_to(ROOT)}")
for p in test_dir.rglob("*.test.ts"):
    print(f"    {p.relative_to(ROOT)}")

print("\n" + "=" * 70)
print(" AUDIT COMPLETE")
print("=" * 70)
