import pytest
from app.engines.strategy.performance_aggregator import (
    compute_strategy_performance,
    compute_all_strategies_performance,
    MIN_RELIABLE_SAMPLE
)
from app.engines.strategy.decay_sync import (
    compute_decay_from_trade_dicts,
    build_decay_map_from_trades
)
from app.engines.strategy.decay_detector import DecayDetector
from app.models.trade import Trade


# ============================================================
# JOURNAL / TRADE MODEL TESTS
# ============================================================
def test_trade_model_has_all_journal_fields():
    cols = [c.name for c in Trade.__table__.columns]
    required = [
        "symbol", "timeframe", "strategy_name", "direction",
        "entry_fill", "stop_loss", "take_profit", "position_size_lots",
        "risk_amount", "rr_planned", "pnl", "realized_r", "result",
        "market_regime", "structure_context", "liquidity_context",
        "confidence", "notes", "screenshot_ref", "status",
        "opened_at", "closed_at"
    ]
    for field in required:
        assert field in cols, f"Missing field: {field}"


# ============================================================
# PERFORMANCE AGGREGATOR TESTS
# ============================================================
def test_performance_profitable_sequence():
    trades = [
        {"pnl": 200, "realized_r": 2.0},
        {"pnl": 150, "realized_r": 1.5},
        {"pnl": -50, "realized_r": -0.5},
        {"pnl": 300, "realized_r": 3.0},
        {"pnl": -100, "realized_r": -1.0},
    ]
    perf = compute_strategy_performance("LIQ_SWEEP", trades)
    assert perf.total_trades == 5
    assert perf.wins == 3
    assert perf.losses == 2
    assert perf.win_rate == 60.0
    assert perf.profit_factor > 1.0
    assert perf.expectancy > 0
    assert perf.total_pnl == 500.0
    assert perf.best_trade_pnl == 300.0
    assert perf.worst_trade_pnl == -100.0


def test_performance_losing_sequence():
    trades = [
        {"pnl": -100, "realized_r": -1.0},
        {"pnl": -150, "realized_r": -1.5},
        {"pnl": -50, "realized_r": -0.5},
        {"pnl": 20, "realized_r": 0.2},
    ]
    perf = compute_strategy_performance("MEAN_REV", trades)
    assert perf.wins == 1
    assert perf.losses == 3
    assert perf.win_rate == 25.0
    assert perf.total_pnl < 0
    assert perf.profit_factor < 1.0


def test_performance_breakeven_trades_counted():
    trades = [
        {"pnl": 0, "realized_r": 0.0},
        {"pnl": 100, "realized_r": 1.0},
        {"pnl": 0, "realized_r": 0.0},
    ]
    perf = compute_strategy_performance("TEST", trades)
    assert perf.breakeven == 2
    assert perf.wins == 1


def test_performance_empty_dataset():
    perf = compute_strategy_performance("EMPTY", [])
    assert perf.total_trades == 0
    assert perf.win_rate == 0.0
    assert perf.sample_size_reliable is False


def test_performance_max_drawdown():
    trades = [
        {"pnl": 100, "realized_r": 1.0},
        {"pnl": -200, "realized_r": -2.0},
        {"pnl": -100, "realized_r": -1.0},
        {"pnl": 300, "realized_r": 3.0},
    ]
    perf = compute_strategy_performance("DD_TEST", trades)
    assert perf.max_drawdown_pct > 0
    assert perf.max_consecutive_losses == 2


def test_performance_sample_size_reliability():
    small = [{"pnl": 10, "realized_r": 0.5}] * 5
    large = [{"pnl": 10, "realized_r": 0.5}] * 15
    assert compute_strategy_performance("S", small).sample_size_reliable is False
    assert compute_strategy_performance("L", large).sample_size_reliable is True


def test_all_strategies_performance_grouping():
    trades = [
        {"strategy_name": "A", "pnl": 100, "realized_r": 1.0},
        {"strategy_name": "A", "pnl": -50, "realized_r": -0.5},
        {"strategy_name": "B", "pnl": 200, "realized_r": 2.0},
    ]
    results = compute_all_strategies_performance(trades)
    assert "A" in results
    assert "B" in results
    assert results["A"].total_trades == 2
    assert results["B"].total_trades == 1


# ============================================================
# DECAY SYNC TESTS
# ============================================================
def test_decay_healthy_performance():
    trades = [{"pnl": 50, "realized_r": 0.5}] * 12
    result = compute_decay_from_trade_dicts(trades, "HEALTHY_STRAT")
    assert result["decay_status"] == "HEALTHY"
    assert result["sample_reliable"] is True


def test_decay_watch_state():
    trades = [{"pnl": -30, "realized_r": -0.3}] * 8 + [{"pnl": 20, "realized_r": 0.2}] * 4
    result = compute_decay_from_trade_dicts(trades, "WATCH_STRAT")
    assert result["decay_status"] in ["WATCH", "DEGRADED"]


def test_decay_degraded_performance():
    trades = [{"pnl": -100, "realized_r": -1.0}] * 10 + [{"pnl": 10, "realized_r": 0.1}] * 2
    result = compute_decay_from_trade_dicts(trades, "DEGRADED_STRAT")
    assert result["decay_status"] == "DEGRADED"


def test_decay_suspended_critical_drawdown():
    trades = [
        {"pnl": 100, "realized_r": 1.0},
        {"pnl": -500, "realized_r": -5.0},
        {"pnl": -400, "realized_r": -4.0},
        {"pnl": -300, "realized_r": -3.0},
        {"pnl": -200, "realized_r": -2.0},
        {"pnl": -100, "realized_r": -1.0},
    ]
    result = compute_decay_from_trade_dicts(trades, "SUSPENDED_STRAT")
    assert result["decay_status"] in ["DEGRADED", "SUSPENDED"]


def test_decay_insufficient_sample():
    trades = [{"pnl": -100, "realized_r": -1.0}] * 3
    result = compute_decay_from_trade_dicts(trades, "SMALL")
    assert result["decay_status"] == "ACTIVE"
    assert result["sample_reliable"] is False


def test_decay_recovery():
    # Sequence of mild losses followed by strong winning streak
    mild_losses = [{"pnl": -10, "realized_r": -0.1}] * 4
    strong_wins = [{"pnl": 80, "realized_r": 1.2}] * 10
    result = compute_decay_from_trade_dicts(mild_losses + strong_wins, "RECOVERY")
    assert result["decay_status"] in ["HEALTHY", "WATCH"]


def test_build_decay_map_multiple_strategies():
    trades = [
        {"strategy_name": "A", "pnl": 50, "realized_r": 0.5},
        {"strategy_name": "A", "pnl": 60, "realized_r": 0.6},
        {"strategy_name": "B", "pnl": -100, "realized_r": -1.0},
        {"strategy_name": "B", "pnl": -80, "realized_r": -0.8},
    ] * 4
    decay_map = build_decay_map_from_trades(trades)
    assert "A" in decay_map
    assert "B" in decay_map
    assert decay_map["A"] in ["HEALTHY", "ACTIVE"]


# ============================================================
# INTEGRATION: SAFETY GATE STILL OVERRIDES
# ============================================================
def test_safety_gate_overrides_strategy_match():
    from app.engines.scoring.no_trade_engine import evaluate_no_trade
    from types import SimpleNamespace
    snap = SimpleNamespace(trend_direction="bullish", atr=0.001)
    scoring = SimpleNamespace(total=40.0)
    result = evaluate_no_trade(result=scoring, snap=snap, rr_ratio=0.5)
    assert result.should_trade is False
    assert result.vetoed is True
