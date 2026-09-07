import pytest
from app.engines.strategy.strategy_registry import get_builtin_strategies, get_strategy_by_id
from app.engines.strategy.smc_strategy_matcher import match_single_strategy, rank_all_strategies, DECAY_PENALTIES
from app.engines.strategy.decay_detector import DecayDetector, StrategyMetrics
from app.engines.intelligence.orchestrator import MarketIntelligenceOrchestrator


# 1. Strategy Registry Tests
def test_strategy_registry_contains_five_institutional_strategies():
    strats = get_builtin_strategies()
    assert len(strats) == 5
    ids = [s["strategy_id"] for s in strats]
    assert "LIQ_SWEEP_CONTINUATION" in ids
    assert "ICT_SILVER_BULLET" in ids
    assert "LONDON_BREAKOUT" in ids
    assert "MEAN_REVERSION" in ids
    assert "TREND_CONTINUATION" in ids


def test_strategy_metadata_has_required_fields():
    strat = get_strategy_by_id("LIQ_SWEEP_CONTINUATION")
    assert strat is not None
    assert "rules" in strat
    rules = strat["rules"]
    assert "market_regimes" in rules
    assert "sessions" in rules
    assert "volatility_filters" in rules
    assert "min_acceptable_rr" in rules
    assert "required_confirmations" in rules


# 2. Deterministic Strategy Matching Tests
def test_trending_bullish_market_matches_trend_continuation_and_sweep():
    market_state = {
        "regime": "TRENDING_BULLISH",
        "session": "LONDON",
        "volatility_percentile": 50.0,
        "atr": 0.0015
    }
    structure_data = {
        "structure_bias": "BULLISH",
        "last_event": "BULLISH_BOS",
        "bos_detected": True,
        "choch_detected": False
    }
    liquidity_data = {
        "total_fvg_count": 2,
        "unmitigated_fvg_count": 2,
        "bullish_fvg_open": 2,
        "bearish_fvg_open": 0
    }

    ranking = rank_all_strategies(market_state, structure_data, liquidity_data, direction="BUY")
    assert ranking["best_strategy"] is not None
    best_id = ranking["best_strategy"]["strategy_id"]
    assert best_id in ["TREND_CONTINUATION", "LIQ_SWEEP_CONTINUATION", "ICT_SILVER_BULLET"]
    assert ranking["best_strategy"]["final_strategy_score"] >= 70.0


def test_ranging_market_selects_mean_reversion_and_rejects_trend_continuation():
    market_state = {
        "regime": "RANGING",
        "session": "LONDON",
        "volatility_percentile": 30.0,
        "atr": 0.0010
    }
    structure_data = {
        "structure_bias": "NEUTRAL",
        "last_event": "CONSOLIDATION",
        "bos_detected": False,
        "choch_detected": False
    }
    liquidity_data = {
        "total_fvg_count": 0,
        "unmitigated_fvg_count": 0,
        "bullish_fvg_open": 0,
        "bearish_fvg_open": 0
    }

    ranking = rank_all_strategies(market_state, structure_data, liquidity_data, direction="BUY")
    ranks = {r["strategy_id"]: r for r in ranking["strategy_ranking"]}
    
    # Mean Reversion should have compatible regime
    mean_rev = ranks["MEAN_REVERSION"]
    assert "Regime 'RANGING' is compatible" in mean_rev["matched_conditions"]
    
    # Trend Continuation should reject RANGING regime
    trend_cont = ranks["TREND_CONTINUATION"]
    assert any("Regime 'RANGING' not in allowed" in c for c in trend_cont["conflicting_conditions"])


# 3. Strategy Decay Engine & Ranking Adjustment Tests
def test_degraded_strategy_receives_score_penalty():
    market_state = {"regime": "TRENDING_BULLISH", "session": "LONDON", "volatility_percentile": 50.0}
    structure_data = {"structure_bias": "BULLISH", "bos_detected": True, "choch_detected": False}
    liquidity_data = {"unmitigated_fvg_count": 1, "bullish_fvg_open": 1, "total_fvg_count": 1}

    # Rank with Healthy
    healthy_ranking = rank_all_strategies(
        market_state, structure_data, liquidity_data, direction="BUY",
        decay_map={"TREND_CONTINUATION": "HEALTHY"}
    )
    tc_healthy = next(r for r in healthy_ranking["strategy_ranking"] if r["strategy_id"] == "TREND_CONTINUATION")

    # Rank with Degraded (-20 penalty)
    degraded_ranking = rank_all_strategies(
        market_state, structure_data, liquidity_data, direction="BUY",
        decay_map={"TREND_CONTINUATION": "DEGRADED"}
    )
    tc_degraded = next(r for r in degraded_ranking["strategy_ranking"] if r["strategy_id"] == "TREND_CONTINUATION")

    assert tc_degraded["decay_adjustment"] == -20.0
    assert tc_degraded["final_strategy_score"] == tc_healthy["final_strategy_score"] - 20.0


def test_suspended_retired_strategy_is_heavily_penalized():
    market_state = {"regime": "TRENDING_BULLISH", "session": "LONDON", "volatility_percentile": 50.0}
    structure_data = {"structure_bias": "BULLISH", "bos_detected": True, "choch_detected": False}
    liquidity_data = {"unmitigated_fvg_count": 1, "bullish_fvg_open": 1, "total_fvg_count": 1}

    ranking = rank_all_strategies(
        market_state, structure_data, liquidity_data, direction="BUY",
        decay_map={"TREND_CONTINUATION": "RETIRED"}
    )
    tc_retired = next(r for r in ranking["strategy_ranking"] if r["strategy_id"] == "TREND_CONTINUATION")
    assert tc_retired["final_strategy_score"] == 0.0
    assert tc_retired["recommendation"] == "REJECTED"


# 4. End-to-End Orchestrator Integration Test
@pytest.mark.asyncio
async def test_orchestrator_returns_strategy_intelligence():
    orchestrator = MarketIntelligenceOrchestrator()
    result = await orchestrator.run_analysis(
        symbol="EUR/USD",
        timeframe="1h",
        direction="BUY",
        account_balance=10000.0,
        risk_percent=1.0
    )
    assert result is not None
    assert "strategy_intelligence" in result
    strat_intel = result["strategy_intelligence"]
    assert "strategy_ranking" in strat_intel
    assert len(strat_intel["strategy_ranking"]) == 5
    assert "best_strategy_name" in strat_intel
    assert "evaluated_count" in strat_intel
    assert strat_intel["evaluated_count"] == 5
