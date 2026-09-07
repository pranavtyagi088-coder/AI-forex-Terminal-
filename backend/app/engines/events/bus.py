import time
import uuid
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from pydantic import BaseModel, Field


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    EMERGENCY = "EMERGENCY"


class EventType(str, Enum):
    TRADE_PROPOSAL_STAGED = "TRADE_PROPOSAL_STAGED"
    TRADE_APPROVED = "TRADE_APPROVED"
    TRADE_EXECUTED = "TRADE_EXECUTED"
    TRADE_CLOSED = "TRADE_CLOSED"
    NO_TRADE_DECISION = "NO_TRADE_DECISION"
    CIRCUIT_BREAKER_STATE_CHANGE = "CIRCUIT_BREAKER_STATE_CHANGE"
    STRATEGY_DECAY_CHANGE = "STRATEGY_DECAY_CHANGE"
    ACCOUNT_FRESHNESS_ANOMALY = "ACCOUNT_FRESHNESS_ANOMALY"
    SPREAD_LIMIT_BREACH = "SPREAD_LIMIT_BREACH"
    SYSTEM_ALERT = "SYSTEM_ALERT"


class TerminalEvent(BaseModel):
    event_id: str
    event_type: EventType
    severity: EventSeverity
    timestamp: float = Field(default_factory=time.time)
    source_module: str
    symbol: Optional[str] = None
    message: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class UnifiedEventBus:
    """Thread-safe, decoupled Pub/Sub Event Hub with rolling ring-buffer audit history."""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self._history: List[TerminalEvent] = []
        self._subscribers: Dict[EventType, List[Callable[[TerminalEvent], None]]] = {}

    def subscribe(self, event_type: EventType, callback: Callable[[TerminalEvent], None]):
        """Register a listener for a specific event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(
        self,
        event_type: EventType,
        severity: EventSeverity,
        source_module: str,
        message: str,
        symbol: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> TerminalEvent:
        """Publish an event, store in history buffer, and notify subscribers."""
        event = TerminalEvent(
            event_id=f"EVT-{uuid.uuid4().hex[:10].upper()}",
            event_type=event_type,
            severity=severity,
            timestamp=time.time(),
            source_module=source_module,
            symbol=symbol.upper() if symbol else None,
            message=message,
            payload=payload or {},
        )

        self._history.append(event)
        if len(self._history) > self.max_history:
            self._history.pop(0)

        # Notify direct subscribers
        listeners = self._subscribers.get(event_type, [])
        for listener in listeners:
            try:
                listener(event)
            except Exception:
                pass  # Subscriber errors must never break the publishing thread

        return event

    def get_recent_events(
        self,
        limit: int = 50,
        severity: Optional[EventSeverity] = None,
        event_type: Optional[EventType] = None,
    ) -> List[TerminalEvent]:
        """Fetch filtered recent events in descending chronological order."""
        filtered = self._history
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        return sorted(filtered, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear(self):
        self._history.clear()


# Global Singleton EventBus Instance
event_bus = UnifiedEventBus()
