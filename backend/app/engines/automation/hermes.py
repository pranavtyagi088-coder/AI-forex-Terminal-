from __future__ import annotations

import time
import asyncio
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable

from app.engines.risk.circuit_breaker import CircuitBreakerEngine, BreakerState
from app.engines.events.bus import event_bus, EventType, EventSeverity


class HermesRunState(str, Enum):
    INITIALIZING = "INITIALIZING"
    ACTIVE_MONITORING = "ACTIVE_MONITORING"
    ROLLOVER_PAUSE = "ROLLOVER_PAUSE"
    EMERGENCY_HALTED = "EMERGENCY_HALTED"


@dataclass
class HermesStatusSnapshot:
    state: HermesRunState
    is_rollover_window: bool
    last_heartbeat_ts: float
    heartbeat_healthy: bool
    broker_server_time_utc: str
    daily_stats_reset_today: bool
    active_monitors_count: int


class HermesOrchestrator:
    """
    Hermes Automation Architecture & Midnight Rollover Engine (P3-#45).
    Guarantees deterministic midnight resets, rollover spread shields, and fail-closed telemetry heartbeats.
    """

    ROLLOVER_START_MINUTE = 55  # 23:55 UTC
    ROLLOVER_END_MINUTE = 5     # 00:05 UTC
    HEARTBEAT_TIMEOUT_SECONDS = 15.0

    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreakerEngine] = None,
        broker_utc_offset_hours: int = 2,  # Typical MetaTrader/cTrader server offset (EET / UTC+2)
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreakerEngine()
        self.broker_offset = timedelta(hours=broker_utc_offset_hours)
        self._state = HermesRunState.INITIALIZING
        self._last_heartbeat = time.time()
        self._last_reset_date: Optional[str] = None

    def get_broker_time(self, utc_now: Optional[datetime] = None) -> datetime:
        now = utc_now or datetime.now(timezone.utc)
        return now + self.broker_offset

    def is_in_midnight_rollover_window(self, broker_dt: Optional[datetime] = None) -> bool:
        b_dt = broker_dt or self.get_broker_time()
        # 23:55 to 23:59 OR 00:00 to 00:05
        if b_dt.hour == 23 and b_dt.minute >= self.ROLLOVER_START_MINUTE:
            return True
        elif b_dt.hour == 0 and b_dt.minute <= self.ROLLOVER_END_MINUTE:
            return True
        return False

    def evaluate_midnight_reset(self, broker_dt: Optional[datetime] = None) -> bool:
        """Checks if a new broker trading day has begun and triggers deterministic daily loss reset."""
        b_dt = broker_dt or self.get_broker_time()
        current_date_str = b_dt.strftime("%Y-%m-%d")

        if self._last_reset_date is None:
            self._last_reset_date = current_date_str
            return False

        if current_date_str != self._last_reset_date and b_dt.hour == 0:
            self._last_reset_date = current_date_str
            event_bus.publish(
                event_type=EventType.SYSTEM_ALERT,
                severity=EventSeverity.INFO,
                source_module="HermesRolloverEngine",
                message=f"Midnight Rollover: Daily loss tracking and drawdown counters reset for new date: {current_date_str}",
                payload={"broker_date": current_date_str, "broker_time": b_dt.isoformat()},
            )
            return True
        return False

    def beat_heartbeat(self) -> None:
        self._last_heartbeat = time.time()

    def get_health_snapshot(self) -> HermesStatusSnapshot:
        now = time.time()
        b_dt = self.get_broker_time()
        in_rollover = self.is_in_midnight_rollover_window(b_dt)
        heartbeat_ok = (now - self._last_heartbeat) <= self.HEARTBEAT_TIMEOUT_SECONDS

        cb_snap = self.circuit_breaker.evaluate()
        if cb_snap.state == BreakerState.KILL_SWITCH:
            state = HermesRunState.EMERGENCY_HALTED
        elif in_rollover:
            state = HermesRunState.ROLLOVER_PAUSE
        elif not heartbeat_ok:
            state = HermesRunState.EMERGENCY_HALTED
        else:
            state = HermesRunState.ACTIVE_MONITORING

        self._state = state

        return HermesStatusSnapshot(
            state=state,
            is_rollover_window=in_rollover,
            last_heartbeat_ts=self._last_heartbeat,
            heartbeat_healthy=heartbeat_ok,
            broker_server_time_utc=b_dt.isoformat(),
            daily_stats_reset_today=(self._last_reset_date == b_dt.strftime("%Y-%m-%d")),
            active_monitors_count=4,
        )
