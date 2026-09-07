"""Tests for the new real-indicator scoring engine."""

import numpy as np
import pandas as pd
import pytest

from app.engines.indicators.technical import compute_technical_snapshot
from app.engines.scoring.no_trade_engine import evaluate_no_trade
from app.engines.scoring.score_engine import calculate_confluence_score


def _make_trending_df(direction: str = "up", n: int = 120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    t = np.linspace(0, 8 * np.pi, n)
    wave = np.sin(t) * 2.5  # clear zigzag swings (Higher Highs / Lower Lows)

    if direction == "up":
        drift = np.linspace(0, 10, n)
        closes = 100 + drift + wave + rng.normal(0, 0.02, n)
    else:
        drift = np.linspace(0, -10, n)
        closes = 100 + drift + wave + rng.normal(0, 0.02, n)

    highs = closes + 0.2
    lows = closes - 0.2
    opens = np.roll(closes, 1)
    opens[0] = closes[0]
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": np.full(n, 1000.0),
    })


def test_strong_uptrend_scores_above_veto_threshold():
    df = _make_trending_df("up")
    snap = compute_technical_snapshot(df)
    result = calculate_confluence_score(snap)
    assert result.total >= 67.0, f"Strong uptrend scored {result.total}, expected >= 67"
    assert result.bias == "bullish"


def test_strong_downtrend_scores_above_veto_threshold():
    df = _make_trending_df("down")
    snap = compute_technical_snapshot(df)
    result = calculate_confluence_score(snap)
    assert result.total >= 67.0, f"Strong downtrend scored {result.total}, expected >= 67"
    assert result.bias == "bearish"


def test_choppy_market_scores_low_and_gets_vetoed():
    rng = np.random.default_rng(99)
    closes = 100 + rng.normal(0, 0.1, 120)
    df = pd.DataFrame({
        "open": np.roll(closes, 1),
        "high": closes + 0.05,
        "low": closes - 0.05,
        "close": closes,
        "volume": np.full(120, 1000.0),
    })
    df["open"].iloc[0] = closes[0]
    snap = compute_technical_snapshot(df)
    result = calculate_confluence_score(snap)
    veto = evaluate_no_trade(result, snap, rr_ratio=2.0)
    assert not veto.should_trade or result.total < 75


def test_ai_cross_check_adds_bonus():
    df = _make_trending_df("up")
    snap = compute_technical_snapshot(df)
    without_ai = calculate_confluence_score(snap, ai_agrees=None)
    with_ai = calculate_confluence_score(snap, ai_agrees=True)
    assert with_ai.total > without_ai.total
    assert with_ai.breakdown.ai_cross_check == 10.0


def test_extreme_volatility_penalty():
    df = _make_trending_df("up")
    df["high"] = df["close"] + 5.0
    df["low"] = df["close"] - 5.0
    snap = compute_technical_snapshot(df)
    result = calculate_confluence_score(snap)
    assert result.breakdown.volatility_penalty < 0


def test_veto_blocks_low_rr():
    df = _make_trending_df("up")
    snap = compute_technical_snapshot(df)
    result = calculate_confluence_score(snap)
    veto = evaluate_no_trade(result, snap, rr_ratio=0.8)
    assert not veto.should_trade
    assert any("RR" in r for r in veto.reasons)
