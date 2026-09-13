import sys
import inspect
from pathlib import Path

print("="*75)
print("🔍 STEP 1: AUDITING EXISTING TRADE MODELS & ENGINES FOR ANALYTICS")
print("="*75)

# 1. Audit Trade ORM Model fields
try:
    from backend.app.models.trade import Trade
    print("\n✅ Trade ORM Model Fields:")
    for col in Trade.__table__.columns:
        print(f"   - {col.name}: {col.type} (nullable={col.nullable})")
except Exception as e:
    print(f"❌ Error loading Trade model: {e}")

# 2. Check existing engines
engines_dir = Path("backend/app/engines")
if engines_dir.exists():
    existing_engines = [p.name for p in engines_dir.iterdir() if p.is_dir() or p.suffix == ".py"]
    print(f"\n✅ Existing Engines: {existing_engines}")
    
    analytics_dir = engines_dir / "analytics"
    print(f"   - Analytics engine dir: {'EXISTS' if analytics_dir.exists() else 'MISSING (Will Create)'}")

# 3. Check existing analytics routes in API
api_routes_dir = Path("backend/app/api/routes")
if api_routes_dir.exists():
    routes = [p.name for p in api_routes_dir.iterdir() if p.suffix == ".py"]
    print(f"\n✅ Existing API Routes: {routes}")
    print(f"   - analytics.py route: {'EXISTS' if (api_routes_dir / 'analytics.py').exists() else 'MISSING (Will Create)'}")

print("\n" + "="*75)
print("\033[92;1m>>> STEP 1: ANALYTICS AUDIT COMPLETED SUCCESSFULLY <<<\033[0m")
print("="*75)
