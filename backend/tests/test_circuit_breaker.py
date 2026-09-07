import os
import json
import pytest
from app.engines.risk.circuit_breaker import (
    BreakerState,
    BreakerThresholds,
    CircuitBreakerEngine,
    _BREAKER_STATE_FILE,
)


@pytest.fixture(autouse=True)
def cleanup_breaker_state():
    """Remove persisted breaker state before and after each test."""
    if os.path.exists(_BREAKER_STATE_FILE):
        os.remove(_BREAKER_STATE_FILE)
    yield
    if os.path.exists(_BREAKER_STATE_FILE):
        os.remove(_BREAKER_STATE_FILE)


class TestCircuitBreakerStateTransitions:
    """Test all state escalation paths."""

    def test_normal_state_when_all_healthy(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=1.0, total_dd_pct=2.0, consecutive_losses=0, health_score=90.0)
        assert snap.state == BreakerState.NORMAL
        assert snap.allowed_to_trade is True
        assert snap.max_risk_multiplier == 1.0

    def test_warning_on_daily_loss_threshold(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=3.5, total_dd_pct=2.0, consecutive_losses=0, health_score=90.0)
        assert snap.state == BreakerState.WARNING
        assert snap.allowed_to_trade is True
        assert snap.max_risk_multiplier == 0.75

    def test_restricted_on_total_dd_threshold(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=1.0, total_dd_pct=8.5, consecutive_losses=0, health_score=90.0)
        assert snap.state == BreakerState.RESTRICTED
        assert snap.allowed_to_trade is False
        assert snap.max_risk_multiplier == 0.25

    def test_kill_switch_on_daily_loss_critical(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=4.6, total_dd_pct=2.0, consecutive_losses=0, health_score=90.0)
        assert snap.state == BreakerState.KILL_SWITCH
        assert snap.allowed_to_trade is False
        assert snap.max_risk_multiplier == 0.0

    def test_kill_switch_on_consecutive_losses(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=1.0, total_dd_pct=2.0, consecutive_losses=7, health_score=90.0)
        assert snap.state == BreakerState.KILL_SWITCH
        assert snap.allowed_to_trade is False

    def test_kill_switch_on_health_score(self):
        engine = CircuitBreakerEngine()
        snap = engine.evaluate(daily_loss_pct=1.0, total_dd_pct=2.0, consecutive_losses=0, health_score=15.0)
        assert snap.state == BreakerState.KILL_SWITCH
        assert snap.allowed_to_trade is False

    def test_state_only_escalates_never_auto_downgrades(self):
        engine = CircuitBreakerEngine()
        # First escalate to WARNING
        engine.evaluate(daily_loss_pct=3.5, total_dd_pct=2.0, consecutive_losses=0, health_score=90.0)
        assert engine.state == BreakerState.WARNING

        # Now metrics improve but state should NOT auto-downgrade
        snap = engine.evaluate(daily_loss_pct=1.0, total_dd_pct=2.0, consecutive_losses=0, health_score=95.0)
        assert snap.state == BreakerState.WARNING  # Still WARNING!

    def test_kill_switch_persists_across_instances(self):
        """Simulate restart: create engine, kill it, create new engine."""
        engine1 = CircuitBreakerEngine()
        engine1.force_kill("Emergency test kill")
        assert engine1.state == BreakerState.KILL_SWITCH

        # New instance (simulates server restart)
        engine2 = CircuitBreakerEngine()
        assert engine2.state == BreakerState.KILL_SWITCH
        snap = engine2.evaluate(daily_loss_pct=0.0, total_dd_pct=0.0, consecutive_losses=0, health_score=100.0)
        assert snap.state == BreakerState.KILL_SWITCH  # Still dead!

    def test_manual_reset_requires_admin_confirmation(self):
        engine = CircuitBreakerEngine()
        engine.force_kill("Test")
        with pytest.raises(PermissionError):
            engine.manual_reset(admin_confirmed=False)

    def test_manual_reset_works_with_admin_confirmation(self):
        engine = CircuitBreakerEngine()
        engine.force_kill("Test")
        snap = engine.manual_reset(admin_confirmed=True)
        assert snap.state == BreakerState.NORMAL
        assert snap.allowed_to_trade is True


class TestCircuitBreakerFailClosed:
    """Test fail-closed behavior on corrupted state."""

    def test_corrupted_state_file_triggers_kill_switch(self):
        """If state file is garbage, assume KILL_SWITCH."""
        with open(_BREAKER_STATE_FILE, "w") as f:
            f.write("THIS IS NOT JSON {{{")

        engine = CircuitBreakerEngine()
        assert engine.state == BreakerState.KILL_SWITCH

    def test_invalid_state_value_triggers_kill_switch(self):
        """If state value is unknown, assume KILL_SWITCH."""
        with open(_BREAKER_STATE_FILE, "w") as f:
            json.dump({"state": "INVALID_STATE_XYZ"}, f)

        engine = CircuitBreakerEngine()
        assert engine.state == BreakerState.KILL_SWITCH
