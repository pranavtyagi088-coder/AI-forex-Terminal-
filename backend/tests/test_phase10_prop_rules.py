import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.prop_firm.preset_engine import check_news_blackout, check_weekend_holding_risk, PROP_FIRM_PRESETS
from app.services.risk_evaluator import evaluate_trade_risk
from app.models.prop_firm import AccountState, PropFirmProfile
from app.schemas.prop_firm import TradeCheckRequest


def test_prop_firm_presets_loaded():
    assert "ftmo_normal" in PROP_FIRM_PRESETS
    assert "the5ers_high_stakes" in PROP_FIRM_PRESETS
    assert "fundednext_stellar" in PROP_FIRM_PRESETS
    assert PROP_FIRM_PRESETS["ftmo_normal"]["daily_drawdown_pct"] == 5.0
    assert PROP_FIRM_PRESETS["alpha_capital"]["max_drawdown_pct"] == 8.0


def test_news_blackout_blocks_trade_during_window():
    now = datetime.now(timezone.utc)
    imminent_news = [
        {
            "title": "US Non-Farm Payrolls (NFP)",
            "impact": "HIGH",
            "published_at": (now - timedelta(minutes=1)).isoformat()
        }
    ]
    res = check_news_blackout(imminent_news, blackout_window_minutes=2, current_time=now)
    assert res["is_blackout"] is True
    assert "NFP" in res["reason"]


def test_news_blackout_allows_trade_outside_window():
    now = datetime.now(timezone.utc)
    old_news = [
        {
            "title": "US CPI",
            "impact": "HIGH",
            "published_at": (now - timedelta(minutes=15)).isoformat()
        }
    ]
    res = check_news_blackout(old_news, blackout_window_minutes=2, current_time=now)
    assert res["is_blackout"] is False


def test_weekend_holding_risk_detects_friday_close():
    friday_night = datetime(2026, 3, 6, 20, 30, tzinfo=timezone.utc) # A Friday
    res = check_weekend_holding_risk(allow_weekend_holding=False, current_time=friday_night)
    assert res["weekend_breach_risk"] is True
    assert "Weekend Holding Breach Risk" in res["warning"]


@pytest.mark.asyncio
async def test_prop_firm_presets_api_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/prop-firm/presets")
        assert res.status_code == 200
        presets = res.json()
        assert len(presets) >= 4
        preset_ids = [p["id"] for p in presets]
        assert "ftmo_normal" in preset_ids
        assert "fundednext_stellar" in preset_ids
