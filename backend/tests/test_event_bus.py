import pytest
from app.engines.events.bus import UnifiedEventBus, EventType, EventSeverity, TerminalEvent


class TestUnifiedEventBus:
    def test_publish_and_retrieve_event(self):
        bus = UnifiedEventBus(max_history=10)
        evt = bus.publish(
            event_type=EventType.CIRCUIT_BREAKER_STATE_CHANGE,
            severity=EventSeverity.CRITICAL,
            source_module="CircuitBreaker",
            message="Circuit breaker tripped to KILL_SWITCH due to max daily drawdown.",
            symbol="EURUSD",
            payload={"drawdown_pct": 5.2, "threshold_pct": 5.0},
        )

        assert evt.event_id.startswith("EVT-")
        assert evt.severity == EventSeverity.CRITICAL
        assert evt.symbol == "EURUSD"

        recent = bus.get_recent_events(limit=5)
        assert len(recent) == 1
        assert recent[0].event_id == evt.event_id

    def test_subscriber_callback_invoked(self):
        bus = UnifiedEventBus()
        received = []

        def on_no_trade(event: TerminalEvent):
            received.append(event)

        bus.subscribe(EventType.NO_TRADE_DECISION, on_no_trade)

        bus.publish(
            event_type=EventType.NO_TRADE_DECISION,
            severity=EventSeverity.WARNING,
            source_module="PreFlightGatekeeper",
            message="Trade blocked by news blackout.",
            symbol="GBPUSD",
        )

        assert len(received) == 1
        assert received[0].symbol == "GBPUSD"
        assert received[0].source_module == "PreFlightGatekeeper"

    def test_ring_buffer_caps_at_max_history(self):
        bus = UnifiedEventBus(max_history=5)
        for i in range(8):
            bus.publish(
                event_type=EventType.SYSTEM_ALERT,
                severity=EventSeverity.INFO,
                source_module="System",
                message=f"Tick heartbeat {i}",
            )

        events = bus.get_recent_events(limit=20)
        assert len(events) == 5
        assert events[0].message == "Tick heartbeat 7"

    def test_filtering_by_severity_and_type(self):
        bus = UnifiedEventBus()
        bus.publish(EventType.TRADE_EXECUTED, EventSeverity.INFO, "Broker", "Filled", "EURUSD")
        bus.publish(EventType.CIRCUIT_BREAKER_STATE_CHANGE, EventSeverity.CRITICAL, "Safety", "Kill Switch", "EURUSD")
        bus.publish(EventType.NO_TRADE_DECISION, EventSeverity.WARNING, "Gate", "Blocked", "GBPUSD")

        critical_events = bus.get_recent_events(severity=EventSeverity.CRITICAL)
        assert len(critical_events) == 1
        assert critical_events[0].event_type == EventType.CIRCUIT_BREAKER_STATE_CHANGE

        trade_events = bus.get_recent_events(event_type=EventType.TRADE_EXECUTED)
        assert len(trade_events) == 1
        assert trade_events[0].message == "Filled"
