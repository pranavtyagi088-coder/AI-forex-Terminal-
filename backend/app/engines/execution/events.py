from enum import Enum
from typing import Dict, Any, List, Callable
from dataclasses import dataclass

class ExecutionEventType(str, Enum):
    ORDER_EXECUTED = 'ORDER_EXECUTED'
    ORDER_REJECTED = 'ORDER_REJECTED'

@dataclass
class ExecutionEvent:
    event_type: ExecutionEventType
    symbol: str
    data: Dict[str, Any]
    provenance_hash: str

class UnifiedEventBus:
    def __init__(self):
        self._subscribers: List[Callable[[ExecutionEvent], None]] = []
        self.events: List[ExecutionEvent] = []

    def subscribe(self, callback: Callable[[ExecutionEvent], None]) -> None:
        self._subscribers.append(callback)

    def publish(self, event: ExecutionEvent) -> None:
        self.events.append(event)
        for sub in self._subscribers:
            try:
                sub(event)
            except Exception:
                pass  # Fail-safe event dispatching
