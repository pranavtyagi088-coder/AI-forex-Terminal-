import pytest
import time
from app.engines.ai.uncertainty_engine import AIUncertaintyGuard, AISidecarAnalysis, UncertaintyLevel
from app.engines.news.sentiment_engine import NewsSentimentEngine, EconomicEvent, NewsImpactLevel


def test_ai_uncertainty_guard_detects_hallucination_and_zeroes_weight():
    """If AI claims BULLISH but deterministic structure is BEARISH, AI weight must drop to 0.0."""
    ai = AISidecarAnalysis(
        bias="BULLISH",
        confidence=92.0,
        detected_patterns=["Bullish Engulfing"],
        reasoning_summary="Looks very bullish.",
    )

    result = AIUncertaintyGuard.evaluate_ai_evidence(
        ai_analysis=ai,
        deterministic_structure_bias="BEARISH_BOS",
        deterministic_regime="TRENDING_BEARISH_EXPANSION",
    )

    assert result.uncertainty_level == UncertaintyLevel.CRITICAL_HALLUCINATION_SUSPECT
    assert result.hallucination_detected is True
    assert result.effective_ai_weight == 0.0
    assert result.is_usable_as_evidence is False
    assert len(result.contradiction_flags) > 0


def test_ai_uncertainty_guard_approves_aligned_evidence():
    """If AI is aligned with deterministic trend, moderate weight is safely granted."""
    ai = AISidecarAnalysis(
        bias="BULLISH",
        confidence=85.0,
        detected_patterns=["Bullish Flag"],
    )

    result = AIUncertaintyGuard.evaluate_ai_evidence(
        ai_analysis=ai,
        deterministic_structure_bias="BULLISH",
        deterministic_regime="TRENDING_BULLISH_EXPANSION",
    )

    assert result.uncertainty_level == UncertaintyLevel.LOW
    assert result.hallucination_detected is False
    assert result.effective_ai_weight <= 0.15  # Max safe cap
    assert result.is_usable_as_evidence is True


def test_news_sentiment_blackout_window_detection():
    """News engine detects upcoming high-impact FOMC event within 15 minutes."""
    now = time.time()
    events = [
        EconomicEvent(
            event_id="EVT-FOMC-1",
            currency="USD",
            event_name="FOMC Interest Rate Decision",
            impact=NewsImpactLevel.HIGH,
            scheduled_timestamp=now + (15 * 60),  # 15 minutes in future
        )
    ]

    res = NewsSentimentEngine.evaluate_news_window(symbol="EURUSD", events=events, current_timestamp=now)

    assert res.is_in_blackout_window is True
    assert res.volatility_risk_multiplier >= 3.5
    assert res.recommended_action == "HALT_TRADING_STAND_ASIDE"
    assert len(res.active_high_impact_events) > 0


def test_news_sentiment_clear_window_when_no_events():
    """When no events are scheduled, trading is fully permitted."""
    now = time.time()
    res = NewsSentimentEngine.evaluate_news_window(symbol="EURUSD", events=[], current_timestamp=now)
    assert res.is_in_blackout_window is False
    assert res.volatility_risk_multiplier == 1.0
    assert res.recommended_action == "NORMAL_TRADING_PERMITTED"
