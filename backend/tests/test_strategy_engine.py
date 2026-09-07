"""Unit and integration tests for Strategy Matching Engine and Recommendation API."""

import numpy as np
import pandas as pd
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.engines.indicators.technical import TechnicalSnapshot
from app.engines.strategy.market_state import build_market_state, classify_regime
from app.engines.strategy.matching_engine import MatchScore, rank_strategies, score_strategy
from app.main import app

client = TestClient(app)


def _make_dummy_snapshot(adx=30.0, trend="bullish", atr_pct=0.50):
    return TechnicalSnapshot(
        last_close=1.1000,
        bars_used=120,
        trend_direction=trend,
        trend_strength=adx,
        ema_fast=1.1020,
        ema_slow=1.0980,
        momentum_direction="bullish",
        rsi=60.0,
        macd_histogram=0.0010,
        atr=0.0050,
        atr_pct=atr_pct,
        volatility_state="normal",
        swing_highs=[1.1050, 1.1080],
        swing_lows=[1.0920, 1.0950],
        nearest_resistance=1.1050,
        nearest_support=1.0950,
        near_key_level=False,
        structure_confirmed=True,
        structure_bias="bullish",
    )


def test_classify_regime_logic():
    assert classify_regime(30.0, "bullish", 0.5) == "TRENDING_BULLISH"
    assert classify_regime(30.0, "bearish", 0.5) == "TRENDING_BEARISH"
    assert classify_regime(15.0, "sideways", 0.5) == "RANGING"
    assert classify_regime(30.0, "bullish", 2.0) == "HIGH_VOLATILITY_UNCLEAR"


def test_evidence_cap_enforcement():
    snap = _make_dummy_snapshot()
    state = build_market_state("EUR/USD", snap)

    # Level A strategy -> cap 100
    strat_a = {
        "strategy_id": "TEST_A",
        "strategy_name": "Test Strat A",
        "instrument": "EUR/USD",
        "evidence_level": "A",
        "strategy_type": "momentum",
        "market_regimes": ["TRENDING_BULLISH"],
        "sessions": ["ANY"],
    }
    score_a = score_strategy(strat_a, state)
    assert score_a.evidence_cap == 100
    assert score_a.final_score <= 100

    # Level B strategy -> cap 85
    strat_b = {**strat_a, "strategy_id": "TEST_B", "evidence_level": "B"}
    score_b = score_strategy(strat_b, state)
    assert score_b.evidence_cap == 85
    assert score_b.final_score <= 85

    # Level C strategy -> cap 60
    strat_c = {**strat_a, "strategy_id": "TEST_C", "evidence_level": "C"}
    score_c = score_strategy(strat_c, state)
    assert score_c.evidence_cap == 60
    assert score_c.final_score <= 60


def test_strategy_recommend_endpoint():
    # Mock OHLCV generator to allow offline integration testing
    n = 120
    rng = np.random.default_rng(42)
    closes = 1.1000 + np.cumsum(np.full(n, 0.0005)) + rng.normal(0, 0.0001, n)
    mock_df = pd.DataFrame({
        "open": np.roll(closes, 1),
        "high": closes + 0.0010,
        "low": closes - 0.0010,
        "close": closes,
        "volume": np.full(n, 1000.0),
        "datetime": pd.date_range("2026-01-01", periods=n, freq="1h", tz="UTC"),
    })

    with patch("app.api.routes.strategy.get_ohlcv_dataframe", new=AsyncMock(return_value=mock_df)):
        response = client.get(
            "/api/strategy/recommend?symbol=EUR/USD",
            headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EUR/USD"
    assert "market_state" in data
    assert "recommendations" in data
    assert len(data["recommendations"]) > 0
    # Check that highest score is ranked #1
    if len(data["recommendations"]) >= 2:
        assert data["recommendations"][0]["match_score"] >= data["recommendations"][1]["match_score"]
