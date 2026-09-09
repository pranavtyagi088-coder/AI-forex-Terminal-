import pytest
from datetime import datetime, timezone, timedelta
from app.engines.automation.hermes import HermesOrchestrator, HermesRunState
from app.engines.telemetry.hub import TelemetryBroadcaster, CockpitTelemetryPayload
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_hermes_midnight_rollover_window_detection():
    """Hermes identifies 23:55 to 00:05 as rollover spread freeze window."""
    hermes = HermesOrchestrator(broker_utc_offset_hours=0)
    
    # Test 23:58 (Inside Rollover)
    dt_rollover_night = datetime(2024, 5, 10, 23, 58, 0, tzinfo=timezone.utc)
    assert hermes.is_in_midnight_rollover_window(dt_rollover_night) is True

    # Test 00:02 (Inside Rollover)
    dt_rollover_morning = datetime(2024, 5, 11, 0, 2, 0, tzinfo=timezone.utc)
    assert hermes.is_in_midnight_rollover_window(dt_rollover_morning) is True

    # Test 14:30 (Outside Rollover)
    dt_normal = datetime(2024, 5, 11, 14, 30, 0, tzinfo=timezone.utc)
    assert hermes.is_in_midnight_rollover_window(dt_normal) is False


def test_hermes_midnight_daily_loss_reset():
    """Hermes fires daily counter reset when date advances to 00:00."""
    hermes = HermesOrchestrator(broker_utc_offset_hours=0)
    
    day1 = datetime(2024, 5, 10, 20, 0, 0, tzinfo=timezone.utc)
    hermes.evaluate_midnight_reset(day1)

    # Transition to Day 2 at 00:00
    day2 = datetime(2024, 5, 11, 0, 0, 1, tzinfo=timezone.utc)
    did_reset = hermes.evaluate_midnight_reset(day2)
    assert did_reset is True


def test_telemetry_hub_cockpit_snapshot_generation():
    """Telemetry hub compiles live health, circuit breaker, and decision metrics."""
    hub = TelemetryBroadcaster()
    snapshot = hub.generate_cockpit_snapshot()

    assert isinstance(snapshot, CockpitTelemetryPayload)
    assert snapshot.circuit_breaker_state in ("NORMAL", "WARNING", "RESTRICTED", "KILL_SWITCH")
    assert snapshot.system_latency_ms < 5.0
    assert snapshot.is_live_telemetry_healthy is True
