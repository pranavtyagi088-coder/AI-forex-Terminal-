from pathlib import Path

print("="*75)
print("🔍 STEP 2: DEEP AUDIT — EXISTING BROKER UI & TYPE CONTRACTS")
print("="*75)

# 1. Read BrokerBridgePanel.tsx
panel_path = Path("frontend/src/components/cockpit/BrokerBridgePanel.tsx")
if panel_path.exists():
    content = panel_path.read_text(encoding="utf-8-sig")
    lines = content.strip().splitlines()
    print(f"\n📄 BrokerBridgePanel.tsx ({len(lines)} lines):")
    print("-" * 60)
    
    # Check for key indicators
    indicators = {
        "useState/useEffect hooks": "useState" in content or "useEffect" in content,
        "API fetch calls": "fetch(" in content or "axios" in content or "useQuery" in content,
        "WebSocket integration": "WebSocket" in content or "useWebSocket" in content,
        "Account balance display": "balance" in content.lower(),
        "Positions grid": "position" in content.lower() and ("map" in content or "grid" in content.lower()),
        "Emergency close button": "emergency" in content.lower() or "kill" in content.lower() or "liquidat" in content.lower(),
        "Approval queue": "approval" in content.lower() or "proposal" in content.lower(),
        "Loading/Error states": "loading" in content.lower() or "error" in content.lower(),
        "UNAVAILABLE fallback": "UNAVAILABLE" in content,
        "Auth token header": "Authorization" in content or "Bearer" in content or "token" in content.lower(),
    }
    
    for feature, present in indicators.items():
        status = "✅ WIRED" if present else "❌ MISSING"
        print(f"   {status} | {feature}")
    
    # Show first 30 lines for context
    print(f"\n   --- First 30 lines preview ---")
    for i, line in enumerate(lines[:30], 1):
        print(f"   {i:3d} | {line}")
    if len(lines) > 30:
        print(f"   ... ({len(lines) - 30} more lines)")
else:
    print("❌ BrokerBridgePanel.tsx NOT FOUND")

# 2. Read broker.ts types
types_path = Path("frontend/src/types/broker.ts")
if types_path.exists():
    t_content = types_path.read_text(encoding="utf-8-sig")
    t_lines = t_content.strip().splitlines()
    print(f"\n📄 broker.ts ({len(t_lines)} lines):")
    print("-" * 60)
    for line in t_lines:
        print(f"   {line}")
else:
    print("❌ broker.ts NOT FOUND")

# 3. Check API layer for broker endpoints
api_path = Path("frontend/src/api")
if api_path.exists():
    api_files = list(api_path.rglob("*.ts"))
    print(f"\n📄 API Layer Files: {[f.name for f in api_files]}")
    for f in api_files:
        fc = f.read_text(encoding="utf-8-sig")
        if "broker" in fc.lower():
            broker_lines = [l.strip() for l in fc.splitlines() if "broker" in l.lower()]
            print(f"   🔗 {f.name} has broker refs: {broker_lines[:5]}")
else:
    print("❌ frontend/src/api/ directory not found")

# 4. Check Zustand store for broker state
store_dir = Path("frontend/src/store")
if store_dir.exists():
    store_files = list(store_dir.rglob("*.ts"))
    print(f"\n📄 Zustand Stores: {[f.name for f in store_files]}")
    for f in store_files:
        fc = f.read_text(encoding="utf-8-sig")
        if "broker" in fc.lower():
            print(f"   🔗 {f.name} has broker state")
else:
    print("❌ frontend/src/store/ directory not found")

print("\n" + "="*75)
print("\033[92;1m>>> STEP 2: DEEP BROKER UI AUDIT COMPLETED SUCCESSFULLY <<<\033[0m")
print("="*75)
