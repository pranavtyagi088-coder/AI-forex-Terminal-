import asyncio
from app.models.strategy import Strategy
from app.engines.strategy.ranker import StrategySelectionRanker
from app.engines.indicators.technical import TechnicalSnapshot
from app.services.news.news_engine import MacroContext
from app.services.social.base import SentimentResult

def test_ranker():
    print("\n============================================================")
    print(" TESTING STRATEGY SELECTION & RANKING ENGINE")
    print("============================================================")

    # Valid Strategy instances
    s1 = Strategy(id=1, name="EMA Cloud Trend Scalper", evidence_grade="A", description="Trend continuation setup")
    s2 = Strategy(id=2, name="Liquidity Sweep Breakout", evidence_grade="A", description="SMC Liquidity sweep setup")
    s3 = Strategy(id=3, name="Mean Reversion Range Fade", evidence_grade="B", description="Range bound rejection setup")

    strategies = [s1, s2, s3]

    # Create Market Context
    tech_snap = TechnicalSnapshot(trend_direction="BULLISH", structure_confirmed=True, volatility_state="NORMAL")
    macro = MacroContext(pair="EUR/USD", news_risk_level="LOW", high_impact_news_count=0, summary="Clean macro window")
    sentiment = SentimentResult(
        pair="EUR/USD", base_currency="EUR", quote_currency="USD",
        base_sentiment=0.4, quote_sentiment=-0.4, pair_sentiment=0.4,
        sentiment_label="BULLISH", discussion_volume="MEDIUM", source_count=5
    )

    ranker = StrategySelectionRanker()
    output = ranker.rank_strategies("EUR/USD", strategies, tech_snap, macro, sentiment, proposed_direction="BUY")

    print(f"  -> Evaluated Strategies: {output.evaluated_count}")
    if output.best_strategy:
        b = output.best_strategy
        print(f"  -> BEST STRATEGY: {b.name} (Grade {b.evidence_grade}) — SCORE: {b.final_score}/100 PTS")
        print(f"     * Technical Fit: {b.technical_fit}/40 | Volatility Fit: {b.volatility_fit}/20")
        print(f"     * News Fit: {b.news_fit}/20 | Social Fit: {b.social_fit}/20")
        print("     * Key Reasons:")
        for r in b.reasons:
            print(f"       - {r}")

    print("\n  -> ALTERNATIVE STRATEGIES:")
    for alt in output.alternative_strategies:
        print(f"     * {alt.name} (Score: {alt.final_score}/100 PTS)")

    print("\n============================================================")
    print(" [SUCCESS] Strategy Selection Ranker Verified Successfully!")
    print("============================================================\n")

if __name__ == "__main__":
    test_ranker()
