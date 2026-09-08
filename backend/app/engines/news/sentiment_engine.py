from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class NewsImpactLevel(str, Enum):
    HIGH = "HIGH"        # NFP, CPI, FOMC, Rate Decision (Spread widens 4x-8x)
    MEDIUM = "MEDIUM"    # Retail Sales, PMI, Flash GDP
    LOW = "LOW"          # Minor speeches, trade balance
    NONE = "NONE"


@dataclass
class EconomicEvent:
    event_id: str
    currency: str
    event_name: str
    impact: NewsImpactLevel
    scheduled_timestamp: float
    actual_value: Optional[str] = None
    forecast_value: Optional[str] = None
    previous_value: Optional[str] = None


@dataclass
class NewsSentimentResult:
    is_in_blackout_window: bool
    blackout_window_seconds_remaining: float
    active_high_impact_events: List[str]
    sentiment_bias: str  # "HAWKISH_BULLISH", "DOVISH_BEARISH", "NEUTRAL"
    volatility_risk_multiplier: float
    recommended_action: str
    alerts: List[str] = field(default_factory=list)


class NewsSentimentEngine:
    """
    Institutional High-Impact News & Sentiment Engine (P2-#37).
    Monitors economic event schedules and computes pre-news and post-news blackout windows.
    """

    DEFAULT_PRE_NEWS_BLACKOUT_SECONDS = 30 * 60   # 30 minutes before news
    DEFAULT_POST_NEWS_BLACKOUT_SECONDS = 30 * 60  # 30 minutes after news

    @classmethod
    def evaluate_news_window(
        cls,
        symbol: str,
        events: List[EconomicEvent],
        current_timestamp: Optional[float] = None,
        pre_blackout_sec: int = DEFAULT_PRE_NEWS_BLACKOUT_SECONDS,
        post_blackout_sec: int = DEFAULT_POST_NEWS_BLACKOUT_SECONDS,
    ) -> NewsSentimentResult:
        now = current_timestamp or time.time()
        sym_upper = symbol.upper()

        relevant_currencies = [sym_upper[:3], sym_upper[3:6]] if len(sym_upper) == 6 else ["USD"]
        if "XAU" in sym_upper or "GOLD" in sym_upper or "NAS100" in sym_upper or "US30" in sym_upper:
            relevant_currencies.append("USD")

        active_events = []
        alerts = []
        is_blackout = False
        max_remaining_blackout = 0.0
        vol_multiplier = 1.0

        for ev in events:
            if ev.currency not in relevant_currencies:
                continue

            if ev.impact == NewsImpactLevel.HIGH:
                time_diff = ev.scheduled_timestamp - now

                # Pre-news window: within 30 min before
                if 0 <= time_diff <= pre_blackout_sec:
                    is_blackout = True
                    max_remaining_blackout = max(max_remaining_blackout, time_diff)
                    active_events.append(f"{ev.currency} {ev.event_name} (in {int(time_diff / 60)}m)")
                    alerts.append(f"PRE_NEWS_BLACKOUT: {ev.event_name} scheduled soon. Spreads expected to widen.")
                    vol_multiplier = max(vol_multiplier, 3.5)

                # Post-news window: within 30 min after
                elif -post_blackout_sec <= time_diff < 0:
                    is_blackout = True
                    remaining_post = post_blackout_sec + time_diff
                    max_remaining_blackout = max(max_remaining_blackout, remaining_post)
                    active_events.append(f"{ev.currency} {ev.event_name} (released {int(abs(time_diff) / 60)}m ago)")
                    alerts.append(f"POST_NEWS_BLACKOUT: {ev.event_name} just released. High volatility decay in progress.")
                    vol_multiplier = max(vol_multiplier, 4.0)

        action = "HALT_TRADING_STAND_ASIDE" if is_blackout else "NORMAL_TRADING_PERMITTED"

        return NewsSentimentResult(
            is_in_blackout_window=is_blackout,
            blackout_window_seconds_remaining=round(max_remaining_blackout, 0),
            active_high_impact_events=active_events,
            sentiment_bias="NEUTRAL",
            volatility_risk_multiplier=round(vol_multiplier, 1),
            recommended_action=action,
            alerts=alerts,
        )
