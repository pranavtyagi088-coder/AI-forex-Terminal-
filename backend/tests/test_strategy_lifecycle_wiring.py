import pytest
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest
from app.engines.strategy.decay_detector import DecayDetector, StrategyMetrics
from app.models.trade import Trade
from app.engines.events.bus import event_bus, EventType, EventSeverity


@pytest.fixture
def gk():
    return PreFlightGatekeeper()


def test_gatekeeper_vetoes_retired_or_suspended_strategy(gk):
    """Gatekeeper must veto trade requests with RETIRED or SUSPENDED strategy status."""
    for status in ("RETIRED", "SUSPENDED"):
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0800,
            stop_loss=1.0750,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
            strategy_lifecycle_status=status,
        )
        res = gk.evaluate(req)
        assert res.allowed is False
        assert res.approved_lot_size == 0.0
        assert res.gate_checks["strategy_health"] is False
        assert any("STRATEGY_DECAY_VETO" in r for r in res.rejection_reasons)


def test_gatekeeper_applies_50pct_penalty_on_degraded_strategy(gk):
    """Gatekeeper must cut risk & lot size by 50% for DEGRADED strategies."""
    req_normal = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
        strategy_lifecycle_status="ACTIVE",
    )
    res_normal = gk.evaluate(req_normal)

    req_degraded = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
        strategy_lifecycle_status="DEGRADED",
    )
    res_degraded = gk.evaluate(req_degraded)

    assert res_degraded.allowed is True
    assert res_degraded.approved_lot_size == pytest.approx(res_normal.approved_lot_size * 0.5, abs=0.01)
    assert res_degraded.risk_pct == 0.5
    assert any("STRATEGY_DEGRADED" in w for w in res_degraded.warnings)


def test_gatekeeper_emits_caution_warning(gk):
    """Gatekeeper permits full lots on CAUTION but emits surveillance warning."""
    req = PreFlightTradeRequest(
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0800,
        stop_loss=1.0750,
        account_balance=100000.0,
        risk_per_trade_pct=1.0,
        strategy_lifecycle_status="CAUTION",
    )
    res = gk.evaluate(req)
    assert res.allowed is True
    assert any("STRATEGY_CAUTION" in w for w in res.warnings)


def test_decay_detector_transitions_to_degraded_or_retired_on_severe_decay():
    """DecayDetector correctly flags strategies on severe decay or critical drawdown."""
    trades = [
        Trade(status="CLOSED", pnl=-500.0, realized_r=-1.0)
        for _ in range(5)
    ]
    metrics = DecayDetector.compute_metrics(trades, current_lifecycle="ACTIVE")
    
    assert metrics.win_rate == 0.0
    assert metrics.avg_realized_r == -1.0
    assert metrics.lifecycle_status in ("DEGRADED", "CAUTION", "RETIRED")
    assert len(metrics.decay_warnings) > 0


def test_event_bus_publishes_decay_event():
    """Verify EventBus records strategy decay event."""
    event = event_bus.publish(
        event_type=EventType.STRATEGY_DECAY_CHANGE,
        severity=EventSeverity.WARNING,
        source_module="StrategyDecayDetector",
        symbol="EURUSD",
        message="Strategy Trend-Follower shifted ACTIVE -> DEGRADED",
        payload={"strategy_id": 1, "old_status": "ACTIVE", "new_status": "DEGRADED"},
    )
    recent = event_bus.get_recent_events(limit=5, event_type=EventType.STRATEGY_DECAY_CHANGE)
    assert len(recent) > 0
    assert recent[0].event_id == event.event_id
