import sys
import os
from pathlib import Path

# Automatically find repo root
current_path = Path.cwd()
if current_path.name == "frontend" or current_path.name == "backend":
    repo_root = current_path.parent
else:
    repo_root = current_path

backend_path = repo_root / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

print("="*75)
print("🔍 STEP 1: AUDITING EXISTING TRADE MODELS & ENGINES FOR QUANT ANALYTICS")
print("="*75)
print(f"📂 Resolved Repo Root: {repo_root}")

# 1. Audit Trade ORM Model fields
try:
    from app.models.trade import Trade
    print("\n✅ Trade ORM Model Fields:")
    for col in Trade.__table__.columns:
        print(f"   - {col.name}: {col.type} (nullable={col.nullable})")
except Exception as e:
    print(f"❌ Error loading Trade model from app.models.trade: {e}")

# 2. Check existing engines
engines_dir = backend_path / "app" / "engines"
if engines_dir.exists():
    existing_engines = [p.name for p in engines_dir.iterdir() if p.is_dir() or p.suffix == ".py"]
    print(f"\n✅ Existing Engines in app/engines: {existing_engines}")
    
    analytics_dir = engines_dir / "analytics"
    print(f"   - Analytics engine dir: {'EXISTS' if analytics_dir.exists() else 'MISSING (Will Create)'}")

# 3. Check existing analytics routes in API
api_routes_dir = backend_path / "app" / "api" / "routes"
if api_routes_dir.exists():
    routes = [p.name for p in api_routes_dir.iterdir() if p.suffix == ".py"]
    print(f"\n✅ Existing API Routes: {routes}")
    print(f"   - analytics.py route: {'EXISTS' if (api_routes_dir / 'analytics.py').exists() else 'MISSING (Will Create)'}")

# 4. Check existing research/quant engines
print(f"\n✅ Checking Quantitative / Research Modules:")
research_engine = engines_dir / "research"
if research_engine.exists():
    print(f"   - app/engines/research files: {[p.name for p in research_engine.iterdir() if p.suffix == '.py']}")
risk_engine = engines_dir / "risk"
if risk_engine.exists():
    print(f"   - app/engines/risk files: {[p.name for p in risk_engine.iterdir() if p.suffix == '.py']}")

print("\n" + "="*75)
print("\033[92;1m>>> STEP 1: ANALYTICS AUDIT COMPLETED SUCCESSFULLY <<<\033[0m")
print("="*75)
