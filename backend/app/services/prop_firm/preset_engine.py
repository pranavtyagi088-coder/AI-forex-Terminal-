"""
Unified Institutional Prop Firm Compliance Engine.
Evaluates static, relative, and trailing drawdowns, news blackout rules,
weekend holding constraints, and max risk boundaries.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


PROP_FIRM_PRESETS: Dict[str, Dict[str, Any]] = {
    "ftmo_normal": {
        "id": "ftmo_normal",
        "name": "FTMO Standard 2-Step",
        "daily_drawdown_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "drawdown_type": "STATIC",
        "max_loss_basis": "BALANCE",
        "profit_target_pct": 10.0,
        "allow_weekend_holding": False,
        "allow_news_trading": False,
        "news_blackout_minutes": 2,
        "max_open_risk_pct": 3.0,
        "max_lot_per_trade": None,
    },
    "ftmo_swing": {
        "id": "ftmo_swing",
        "name": "FTMO Swing Account",
        "daily_drawdown_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "drawdown_type": "STATIC",
        "max_loss_basis": "BALANCE",
        "profit_target_pct": 10.0,
        "allow_weekend_holding": True,
        "allow_news_trading": True,
        "news_blackout_minutes": 0,
        "max_open_risk_pct": 5.0,
        "max_lot_per_trade": None,
    },
    "the5ers_high_stakes": {
        "id": "the5ers_high_stakes",
        "name": "The5ers High Stakes (Trailing DD)",
        "daily_drawdown_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "drawdown_type": "TRAILING_EQUITY",
        "max_loss_basis": "EQUITY",
        "profit_target_pct": 8.0,
        "allow_weekend_holding": True,
        "allow_news_trading": True,
        "news_blackout_minutes": 0,
        "max_open_risk_pct": 4.0,
        "max_lot_per_trade": None,
    },
    "fundednext_stellar": {
        "id": "fundednext_stellar",
        "name": "FundedNext Stellar 2-Step",
        "daily_drawdown_pct": 5.0,
        "max_drawdown_pct": 10.0,
        "drawdown_type": "STATIC",
        "max_loss_basis": "BALANCE",
        "profit_target_pct": 8.0,
        "allow_weekend_holding": True,
        "allow_news_trading": False,
        "news_blackout_minutes": 2,
        "max_open_risk_pct": 3.5,
        "max_lot_per_trade": None,
    },
    "alpha_capital": {
        "id": "alpha_capital",
        "name": "Alpha Capital Pro",
        "daily_drawdown_pct": 5.0,
        "max_drawdown_pct": 8.0,
        "drawdown_type": "STATIC",
        "max_loss_basis": "BALANCE",
        "profit_target_pct": 8.0,
        "allow_weekend_holding": False,
        "allow_news_trading": False,
        "news_blackout_minutes": 5,
        "max_open_risk_pct": 2.5,
        "max_lot_per_trade": 50.0,
    }
}


def get_preset_profile(preset_id: str) -> Dict[str, Any]:
    return PROP_FIRM_PRESETS.get(preset_id, PROP_FIRM_PRESETS["ftmo_normal"])


def check_news_blackout(
    news_items: Optional[List[Dict[str, Any]]],
    blackout_window_minutes: Optional[int] = 2,
    allow_news_trading: bool = False,
    current_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Checks if current time is within high-impact news blackout window.
    If allow_news_trading is True or blackout window <= 0, blackout is bypassed.
    """
    window = blackout_window_minutes if blackout_window_minutes is not None else 2
    if allow_news_trading or window <= 0 or not news_items:
        return {"is_blackout": False, "reason": None, "active_event": None}

    now = current_time or datetime.now(timezone.utc)

    for item in news_items:
        impact = str(item.get("impact") or item.get("impact_level") or "").upper()
        if impact == "HIGH":
            title = item.get("title", "High-Impact Macro Event")
            pub_str = item.get("published_at")
            if pub_str:
                try:
                    if isinstance(pub_str, str):
                        pub_time = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                    else:
                        pub_time = pub_str
                    diff_mins = abs((now - pub_time).total_seconds()) / 60.0
                    if diff_mins <= window:
                        return {
                            "is_blackout": True,
                            "reason": f"High-Impact news blackout active: '{title}' ({diff_mins:.1f} mins from release, window: +/-{window}m)",
                            "active_event": title
                        }
                except Exception:
                    pass

    return {"is_blackout": False, "reason": None, "active_event": None}


def check_weekend_holding_risk(
    allow_weekend_holding: bool = False,
    current_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Detects Friday market close approaching (>20:00 UTC on Friday)
    for accounts that prohibit weekend holding.
    """
    if allow_weekend_holding:
        return {"weekend_breach_risk": False, "warning": None}

    now = current_time or datetime.now(timezone.utc)
    # Friday is weekday 4
    if now.weekday() == 4 and now.hour >= 20:
        return {
            "weekend_breach_risk": True,
            "warning": "Weekend Holding Breach Risk: Friday market close imminent. All open positions must be flat by 21:00 UTC."
        }
    return {"weekend_breach_risk": False, "warning": None}
