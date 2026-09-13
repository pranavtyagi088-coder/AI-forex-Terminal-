from pathlib import Path
import re

print("="*75)
print("🔍 STEP 3: FINAL PRE-BUILD AUDIT — API/APP/BACKEND CONTRACT LOCK")
print("="*75)

# 1. Check lib/api.ts for broker methods
api_lib = Path("frontend/src/lib/api.ts")
if api_lib.exists():
    content = api_lib.read_text(encoding="utf-8-sig")
    print(f"\n📄 lib/api.ts ({len(content.splitlines())} lines):")
    print("-" * 60)
    
    broker_methods = re.findall(r"(getBroker\w+|approveProposal\w*|emergencyClose\w*|stageProposal\w*|listProposals\w*)", content)
    unique_methods = sorted(set(broker_methods))
    print(f"   🔗 Broker-related methods found: {unique_methods}")
    
    # Check auth
    if "Authorization" in content or "Bearer" in content:
        print(f"   ✅ Auth header: WIRED")
        auth_lines = [l.strip() for l in content.splitlines() if "Bearer" in l or "Authorization" in l or "VITE_API_AUTH" in l]
        for l in auth_lines[:3]:
            print(f"      → {l[:100]}")
    else:
        print(f"   ❌ Auth header: NOT FOUND")
else:
    print("❌ lib/api.ts NOT FOUND")

# 2. Check App.tsx for BrokerBridgePanel mount
app_tsx = Path("frontend/src/App.tsx")
if app_tsx.exists():
    ac = app_tsx.read_text(encoding="utf-8-sig")
    if "BrokerBridgePanel" in ac:
        print(f"\n✅ App.tsx: BrokerBridgePanel is IMPORTED & MOUNTED")
        # Show mount context
        for i, line in enumerate(ac.splitlines()):
            if "BrokerBridgePanel" in line:
                print(f"   Line {i+1}: {line.strip()}")
    else:
        print(f"\n❌ App.tsx: BrokerBridgePanel NOT MOUNTED (needs integration)")
else:
    print("❌ App.tsx NOT FOUND")

# 3. Inspect backend broker routes actual response models
routes_path = Path("backend/app/api/routes/trades.py")
if routes_path.exists():
    rc = routes_path.read_text(encoding="utf-8-sig")
    # Find /broker/ endpoints
    broker_route_blocks = []
    lines = rc.splitlines()
    for i, line in enumerate(lines):
        if "/broker/" in line and ("@router" in line or "get(" in line or "post(" in line):
            # Grab next 25 lines
            block = "\n".join(lines[i:i+30])
            broker_route_blocks.append(block)
    
    print(f"\n📄 Backend /broker/ routes ({len(broker_route_blocks)} found):")
    print("-" * 60)
    for idx, block in enumerate(broker_route_blocks, 1):
        print(f"\n   --- Route {idx} ---")
        for l in block.splitlines()[:20]:
            print(f"   {l}")
else:
    print("❌ backend/app/api/routes/trades.py NOT FOUND")

# 4. Check MT5 adapter actual returned dict keys
mt5_path = Path("backend/app/services/broker/mt5_adapter.py")
if mt5_path.exists():
    mc = mt5_path.read_text(encoding="utf-8-sig")
    # Find get_account_info and get_positions returns
    print(f"\n📄 MT5Adapter Response Keys:")
    print("-" * 60)
    for method in ["get_account_info", "get_positions", "close_position"]:
        idx = mc.find(f"def {method}")
        if idx >= 0:
            snippet = mc[idx:idx+1200]
            print(f"\n   🔧 {method}() snippet:")
            for l in snippet.splitlines()[:35]:
                print(f"   {l}")
else:
    print("❌ mt5_adapter.py NOT FOUND")

print("\n" + "="*75)
print("\033[92;1m>>> STEP 3: FINAL BROKER CONTRACT AUDIT COMPLETED SUCCESSFULLY <<<\033[0m")
print("="*75)
