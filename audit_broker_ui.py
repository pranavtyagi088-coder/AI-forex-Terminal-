import json
import inspect
from pathlib import Path

print("="*75)
print("🔍 STEP 1: AUDITING BROKER BACKEND CONTRACTS & FRONTEND STRUCTURE")
print("="*75)

# 1. Inspect Backend Broker Routes & Models
try:
    from backend.app.services.broker.base import BrokerAccountInfo, BrokerOrderRequest, ExecutionReceipt, PositionInfo
    print("✅ Backend Broker Dataclasses Found:")
    print(f"   - BrokerAccountInfo fields: {list(BrokerAccountInfo.__dataclass_fields__.keys())}")
    print(f"   - PositionInfo fields: {list(PositionInfo.__dataclass_fields__.keys())}")
    print(f"   - ExecutionReceipt fields: {list(ExecutionReceipt.__dataclass_fields__.keys())}")
except Exception as e:
    print(f"❌ Backend Broker Dataclasses Import Error: {e}")

# 2. Check Frontend Directory Layout
fe_dir = Path("frontend/src")
if fe_dir.exists():
    print("\n✅ Frontend Directories:")
    components = [p.name for p in (fe_dir / "components").iterdir() if p.is_dir()]
    print(f"   - Components subfolders: {components}")
    
    # Check if broker types exist
    types_file = fe_dir / "types" / "broker.ts"
    print(f"   - frontend/src/types/broker.ts: {'EXISTS' if types_file.exists() else 'MISSING (Will Create)'}")
    
    # Check Cockpit directory
    cockpit_dir = fe_dir / "components" / "cockpit"
    if cockpit_dir.exists():
        cockpit_files = [p.name for p in cockpit_dir.iterdir() if p.is_file()]
        print(f"   - Existing Cockpit Panels: {cockpit_files}")
else:
    print("❌ frontend/src directory not found!")

print("="*75)
print("\033[92;1m>>> STEP 1: BROKER ARCHITECTURE AUDIT COMPLETED SUCCESSFULLY <<<\033[0m")
print("="*75)
