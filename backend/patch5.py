import os

# FIX 1: config.py version
p = os.path.join("app", "core", "config.py")
c = open(p, "r", encoding="utf-8").read()
c = c.replace("2.0.0", "3.0.0")
open(p, "w", encoding="utf-8").write(c)
print("1. config version fixed")

# FIX 2: system.py version
p = os.path.join("app", "api", "routes", "system.py")
c = open(p, "r", encoding="utf-8").read()
c = c.replace("2.0.0", "3.0.0")
open(p, "w", encoding="utf-8").write(c)
print("2. system version fixed")

# FIX 3: technical.py add atr_pct
p = os.path.join("app", "engines", "indicators", "technical.py")
c = open(p, "r", encoding="utf-8").read()
if "atr_pct" not in c:
    c = c.replace("last_close: float = 0.0", "last_close: float = 0.0\n    atr_pct: float = 50.0")
    c = c.replace("last_close=float(closes[-1]),", "last_close=float(closes[-1]),\n            atr_pct=round(float(atr_val / (closes[-1] if closes[-1] > 0 else 1.0) * 100), 2),")
    c = c.replace("last_close=1.0850)", "last_close=1.0850, atr_pct=50.0)")
    open(p, "w", encoding="utf-8").write(c)
print("3. technical atr_pct fixed")

# FIX 4: market.py bars_count
p = os.path.join("app", "api", "routes", "market.py")
c = open(p, "r", encoding="utf-8").read()
old = '"candles": records}'
new = '"bars_count": len(records), "candles": records}'
c = c.replace(old, new)
open(p, "w", encoding="utf-8").write(c)
print("4. market bars_count fixed")

# FIX 5: performance.py detail endpoint
p = os.path.join("app", "api", "routes", "performance.py")
c = open(p, "r", encoding="utf-8").read()
if "/{strategy_id}" not in c:
    ep = """

@router.get("/{strategy_id}")
async def get_strategy_detail(strategy_id: str, db: AsyncSession = Depends(get_db), _token: str = Depends(verify_api_token)):
    try:
        sid = int(strategy_id)
        res = await db.execute(select(Strategy).where((Strategy.id == strategy_id) | (Strategy.id == sid)))
    except Exception:
        res = await db.execute(select(Strategy).where(Strategy.id == strategy_id))
    strat = res.scalar_one_or_none()
    if not strat:
        raise HTTPException(404, "Strategy not found")
    t_res = await db.execute(select(Trade).where(Trade.status == "CLOSED"))
    trades = [t for t in t_res.scalars().all() if str(t.strategy_id) == str(strat.id)]
    m = DecayDetector.compute_metrics(trades, strat.lifecycle_status)
    return {"strategy_id": str(strat.id), "name": strat.name, "evidence_grade": strat.evidence_grade, "lifecycle_status": m.lifecycle_status, "total_trades": m.total_trades, "win_rate": m.win_rate, "avg_realized_r": m.avg_realized_r, "profit_factor": m.profit_factor, "decay_warnings": m.decay_warnings}
"""
    c = c + ep
    open(p, "w", encoding="utf-8").write(c)
print("5. performance detail endpoint fixed")

# Clean DB
for db in ["forex_terminal.db", "test.db"]:
    if os.path.exists(db):
        try:
            os.remove(db)
        except Exception:
            pass
print("6. DB cleaned")
