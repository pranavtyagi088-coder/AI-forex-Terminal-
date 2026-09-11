"""
Tests for Phase 2C: Liquidity Sweep wiring into Confluence Scoring and Telemetry.
"""
import pytest
from app.engines.intelligence.liquidity_sweep import (
    SweepAnalysisResult,
    SweepEvent,
    SweepDirection,
    LiquidityLevelType,
)
from app.engines.market.confluence import apply_sweep_evidence_to_confluence
from app.engines.telemetry.hub import telemetry_hub


def test_sweep_confluence_bonus_on_aligned_fade_buy():
    """Fading sell-side sweep with BUY order should add bonus confluence points."""
    sweep = SweepEvent(
        timestamp=100.0,
        direction=SweepDirection.SELL_SIDE,
        liquidity_level_price=1.0800,
        level_type=LiquidityLevelType.EQUAL_LOWS,
        confidence_score=0.85,
        is_confirmed=True
    )
    result = SweepAnalysisResult(
        symbol="EURUSD",
        timeframe="H1",
        active_sweep=sweep,
        sweep_bias="FADE_BUY"
    )

    pos_confluences = []
    warnings = []
    final_score = apply_sweep_evidence_to_confluence(
        base_score=60.0,
        proposed_direction="BUY",
        sweep_result=result,
        positive_confluences=pos_confluences,
        negative_warnings=warnings
    )

    assert final_score > 60.0
    assert any("LIQUIDITY_SWEEP_CONFIRMED" in c for c in pos_confluences)
    assert len(warnings) == 0


def test_sweep_confluence_penalty_on_counter_sweep_risk():
    """Buying directly into buy-side sweep should trigger hazard penalty."""
    sweep = SweepEvent(
        timestamp=100.0,
        direction=SweepDirection.BUY_SIDE,
        liquidity_level_price=1.0900,
        level_type=LiquidityLevelType.EQUAL_HIGHS,
        confidence_score=0.80,
        is_confirmed=True
    )
    result = SweepAnalysisResult(
        symbol="EURUSD",
        timeframe="H1",
        active_sweep=sweep,
        sweep_bias="FADE_SELL"
    )

    pos_confluences = []
    warnings = []
    final_score = apply_sweep_evidence_to_confluence(
        base_score=70.0,
        proposed_direction="BUY",
        sweep_result=result,
        positive_confluences=pos_confluences,
        negative_warnings=warnings
    )

    assert final_score < 70.0
    assert any("COUNTER_SWEEP_RISK" in w for w in warnings)


def test_telemetry_hub_snapshot_contains_sweep_intelligence():
    """Verify CockpitTelemetryPayload includes sweep_intelligence dictionary."""
    snap = telemetry_hub.generate_cockpit_snapshot()
    assert hasattr(snap, "sweep_intelligence")
    assert snap.sweep_intelligence.get("sweep_detected") is True
    assert snap.sweep_intelligence.get("bias") == "FADE_SELL"
