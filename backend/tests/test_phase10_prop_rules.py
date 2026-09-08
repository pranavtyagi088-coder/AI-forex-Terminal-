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
    res = check_news_blackout(imminent_news, blackout_window_minutes=2, allow_news_trading=False, current_time=now)
    assert res["is_blackout"] is True
    assert "NFP" in res["reason"]


def test_news_trading_allowed_bypasses_blackout():
    now = datetime.now(timezone.utc)
    imminent_news = [
        {
            "title": "US Non-Farm Payrolls (NFP)",
            "impact": "HIGH",
            "published_at": (now - timedelta(minutes=1)).isoformat()
        }
    ]
    # When allow_news_trading is True (e.g. Swing Accounts), blackout is ignored
    res = check_news_blackout(imminent_news, blackout_window_minutes=2, allow_news_trading=True, current_time=now)
    assert res["is_blackout"] is False


def test_weekend_holding_allowed_bypasses_warning():
    friday_night = datetime(2026, 3, 6, 20, 30, tzinfo=timezone.utc)
    res = check_weekend_holding_risk(allow_weekend_holding=True, current_time=friday_night)
    assert res["weekend_breach_risk"] is False


def test_evaluate_trade_risk_dynamic_max_lot():
    account = AccountState(
        account_id="acc_1",
        profile_id="prof_1",
        starting_balance=100000.0,
        daily_drawdown_limit_usd=5000.0,
        total_drawdown_limit_usd=10000.0,
        current_daily_loss_usd=0.0,
        current_total_loss_usd=0.0
    )
    profile = PropFirmProfile(
        id="prof_1",
        name="Strict Lot Firm",
        max_lot_per_trade=5.0
    )
    trade = TradeCheckRequest(
        pair="EURUSD",
        order_type="BUY",
        lot_size=10.0, # Exceeds 5.0 lot limit
        stop_loss_pips=20.0,
        entry_price=1.0850
    )
    result = evaluate_trade_risk(account, profile, trade)
    assert result.allowed is False
    assert any("EXCEEDS_PROFILE_MAX_LOT_LIMIT" in v for v in result.violations)


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
