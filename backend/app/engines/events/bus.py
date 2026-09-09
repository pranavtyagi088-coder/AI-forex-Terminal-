"""
Unified Event Bus — Pub/Sub + Ring Buffer (1000 events).
Institutional audit backbone with typed enums + TerminalEvent schema + async WS fan-out.
Supports EVT- IDs, reverse-chronological ordering, and full backward compatibility.
"""
from enum import Enum
import uuid
import time
import logging
import asyncio
import inspect
from collections import deque
from typing import Any, Callable, Awaitable, Union, Optional, Dict, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"
    DEBUG = "DEBUG"


class EventType(str, Enum):
    # Legacy / Core Contracts
    NO_TRADE_DECISION = "NO_TRADE_DECISION"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    STRATEGY_DECAY_CHANGE = "STRATEGY_DECAY_CHANGE"
    CIRCUIT_BREAKER_STATE_CHANGE = "CIRCUIT_BREAKER_STATE_CHANGE"

    # Risk & Pre-Flight
    PRE_FLIGHT_REJECTED = "PRE_FLIGHT_REJECTED"
    PRE_FLIGHT_APPROVED = "PRE_FLIGHT_APPROVED"
    RISK_BREACH = "RISK_BREACH"
    CIRCUIT_BREAKER_TRIPPED = "CIRCUIT_BREAKER_TRIPPED"
    CIRCUIT_BREAKER_RESET = "CIRCUIT_BREAKER_RESET"
    DRAWDOWN_BREACH = "DRAWDOWN_BREACH"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    CORRELATION_BREACH = "CORRELATION_BREACH"
    SPREAD_BREACH = "SPREAD_BREACH"

    # Execution & Staging
    ORDER_STAGED = "ORDER_STAGED"
    ORDER_APPROVED = "ORDER_APPROVED"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_EXECUTED = "ORDER_EXECUTED"
    ORDER_CLOSED = "ORDER_CLOSED"
    SLIPPAGE_BREACH = "SLIPPAGE_BREACH"

    # Strategy & Lifecycle
    STRATEGY_DECAY = "STRATEGY_DECAY"
    STRATEGY_STATUS_CHANGED = "STRATEGY_STATUS_CHANGED"
    STRATEGY_DEGRADED = "STRATEGY_DEGRADED"
    STRATEGY_RETIRED = "STRATEGY_RETIRED"
    STRATEGY_CAUTION = "STRATEGY_CAUTION"

    # News & Macro
    NEWS_BLACKOUT = "NEWS_BLACKOUT"
    SENTIMENT_SHIFT = "SENTIMENT_SHIFT"

    # AI & Uncertainty
    AI_UNCERTAINTY = "AI_UNCERTAINTY"
    AI_OVERRIDE = "AI_OVERRIDE"
    AI_HALLUCINATION_DETECTED = "AI_HALLUCINATION_DETECTED"

    # Quantitative
    MONTE_CARLO_COMPLETE = "MONTE_CARLO_COMPLETE"
    STRESS_TEST_ALERT = "STRESS_TEST_ALERT"

    # System & Telemetry
    SYSTEM = "SYSTEM"
    HEARTBEAT = "HEARTBEAT"
    MIDNIGHT_ROLLOVER = "MIDNIGHT_ROLLOVER"
    TELEMETRY_SNAPSHOT = "TELEMETRY_SNAPSHOT"


class TerminalEvent(BaseModel):
    """Institutional canonical event schema with EVT- ID and dual dict/dot access."""
    event_id: str = Field(default_factory=lambda: f"EVT-{uuid.uuid4().hex[:8].upper()}")
    type: Union[EventType, str] = Field(..., description="EventType value")
    severity: Union[EventSeverity, str] = Field(..., description="EventSeverity value")
    source_module: str = Field(..., alias="source", description="Origin module")
    message: str
    symbol: Optional[str] = None
    payload: dict = Field(default_factory=dict)
    timestamp: float = Field(default_factory=lambda: time.time())

    model_config = {
        "populate_by_name": True,
        "extra": "allow",
        "arbitrary_types_allowed": True,
    }

    @property
    def source(self) -> str:
        return self.source_module

    @property
    def event_type(self) -> Union[EventType, str]:
        return self.type

    def __getitem__(self, item: str) -> Any:
        if item == "source":
            return self.source_module
        if item == "event_type":
            return self.type
        return getattr(self, item)

    def get(self, item: str, default: Any = None) -> Any:
        try:
            return self[item]
        except (AttributeError, KeyError):
            return default


class UnifiedEventBus:
    """
    Central institutional event bus with ring buffer and async fan-out subscribers.
    Preserves full audit provenance across live trading, backtesting, and telemetry.
    """

    def __init__(self, buffer_size: int = 1000, max_history: Optional[int] = None):
        limit = max_history if max_history is not None else buffer_size
        self._buffer: deque[TerminalEvent] = deque(maxlen=limit)
        self._subscribers: list[Callable[..., Awaitable[None]]] = []
        self._keyed_subscribers: Dict[str, List[Callable]] = {}

    def publish(
        self,
        event_type: Union[EventType, str],
        severity: Union[EventSeverity, str],
        source_module: str,
        message: str,
        symbol: str | None = None,
        payload: dict | None = None,
        event_id: str | None = None,
    ) -> TerminalEvent:
        try:
            ev_type_enum = EventType(event_type) if isinstance(event_type, str) else event_type
        except (ValueError, KeyError):
            ev_type_enum = event_type

        try:
            ev_sev_enum = EventSeverity(severity) if isinstance(severity, str) else severity
        except (ValueError, KeyError):
            ev_sev_enum = severity

        kwargs: dict[str, Any] = {
            "type": ev_type_enum,
            "severity": ev_sev_enum,
            "source_module": source_module,
            "message": message,
            "symbol": symbol,
            "payload": payload or {},
            "timestamp": time.time(),
        }
        if event_id:
            kwargs["event_id"] = event_id

        terminal_event = TerminalEvent(**kwargs)
        self._buffer.append(terminal_event)

        event_dict = terminal_event.model_dump()

        # ── Fan-out to global async subscribers (WebSocket Broadcaster) ──
        for sub in list(self._subscribers):
            try:
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(sub(event_dict))
                except RuntimeError:
                    asyncio.run(sub(event_dict))
            except Exception as exc:
                logger.error("EventBus subscriber error (isolated): %s", exc)

        # ── Fan-out to legacy keyed subscribers (Sync / Async Callbacks) ──
        ev_type_str = ev_type_enum.value if hasattr(ev_type_enum, "value") else str(ev_type_enum)
        if ev_type_str in self._keyed_subscribers:
            for callback in list(self._keyed_subscribers[ev_type_str]):
                try:
                    if inspect.iscoroutinefunction(callback):
                        try:
                            loop = asyncio.get_running_loop()
                            loop.create_task(callback(terminal_event))
                        except RuntimeError:
                            asyncio.run(callback(terminal_event))
                    else:
                        callback(terminal_event)
                except Exception as exc:
                    logger.error("EventBus keyed subscriber error: %s", exc)

        return terminal_event

    def get_recent_events(
        self,
        limit: int = 50,
        severity: Optional[Union[EventSeverity, str]] = None,
        event_type: Optional[Union[EventType, str]] = None,
    ) -> list[TerminalEvent]:
        """Query events in reverse-chronological order (newest first)."""
        events = list(reversed(self._buffer))
        if severity is not None:
            sev_val = severity.value if hasattr(severity, "value") else str(severity)
            events = [e for e in events if (e.severity.value if hasattr(e.severity, "value") else str(e.severity)) == sev_val]
        if event_type is not None:
            type_val = event_type.value if hasattr(event_type, "value") else str(event_type)
            events = [e for e in events if (e.type.value if hasattr(e.type, "value") else str(e.type)) == type_val]
        return events[:limit]

    def get_recent(self, n: int = 50) -> list[TerminalEvent]:
        return self.get_recent_events(limit=n)

    def get_all(self) -> list[TerminalEvent]:
        return list(reversed(self._buffer))

    def clear(self) -> None:
        self._buffer.clear()

    # ── Legacy Subscription Contract ──
    def subscribe(self, event_type: Union[EventType, str], callback: Callable) -> None:
        ev_val = event_type.value if hasattr(event_type, "value") else str(event_type)
        if ev_val not in self._keyed_subscribers:
            self._keyed_subscribers[ev_val] = []
        if callback not in self._keyed_subscribers[ev_val]:
            self._keyed_subscribers[ev_val].append(callback)

    def unsubscribe(self, event_type: Union[EventType, str], callback: Callable) -> None:
        ev_val = event_type.value if hasattr(event_type, "value") else str(event_type)
        if ev_val in self._keyed_subscribers and callback in self._keyed_subscribers[ev_val]:
            self._keyed_subscribers[ev_val].remove(callback)

    # ── Modern Subscription Contract ──
    def register_subscriber(self, callback: Callable[..., Awaitable[None]]) -> None:
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unregister_subscriber(self, callback: Callable[..., Awaitable[None]]) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers) + sum(len(cb_list) for cb_list in self._keyed_subscribers.values())

    def __len__(self) -> int:
        return len(self._buffer)


# ── Aliases & Singleton Instance ──
EventBus = UnifiedEventBus
event_bus = UnifiedEventBus()
