from fastapi import APIRouter, Depends
from app.core.auth import verify_api_token
from app.engines.telemetry.hub import telemetry_hub, CockpitTelemetryPayload
from app.engines.automation.hermes import HermesOrchestrator, HermesStatusSnapshot

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
hermes = HermesOrchestrator()


@router.get("/cockpit", response_model=CockpitTelemetryPayload)
def get_cockpit_telemetry():
    """Live telemetry stream endpoint for Institutional Risk Cockpit."""
    return telemetry_hub.generate_cockpit_snapshot()


@router.get("/hermes/status")
def get_hermes_automation_status():
    """Returns Hermes automation heartbeat, midnight rollover, and broker time sync."""
    hermes.beat_heartbeat()
    snap = hermes.get_health_snapshot()
    return {
        "state": snap.state.value,
        "is_rollover_window": snap.is_rollover_window,
        "heartbeat_healthy": snap.heartbeat_healthy,
        "broker_server_time": snap.broker_server_time_utc,
        "daily_stats_reset_today": snap.daily_stats_reset_today,
    }
