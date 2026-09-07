import asyncio
from app.services.news.news_engine import NewsImpactEngine
from app.services.social.sentiment_engine import FinancialSentimentEngine
from app.services.social.reddit_provider import RedditSocialProvider

async def verify_intelligence():
    print("\n--- 1. TESTING CENTRAL BANK NEWS ENGINE ---")
    news_engine = NewsImpactEngine()
    macro = await news_engine.get_macro_context("EUR/USD")
    print(f"  -> Pair: {macro.pair}")
    print(f"  -> News Risk Level: {macro.news_risk_level}")
    print(f"  -> High Impact Events: {macro.high_impact_news_count}")
    print(f"  -> Articles Fetched: {len(macro.articles)}")
    for a in macro.articles[:2]:
        print(f"     * [{a.source}] {a.title} ({a.pub_date[:16]})")

    print("\n--- 2. TESTING SOCIAL SENTIMENT ENGINE ---")
    reddit = RedditSocialProvider()
    posts = await reddit.fetch_posts("EUR/USD", limit=5)
    
    sentiment_engine = FinancialSentimentEngine()
    sent_res = sentiment_engine.aggregate_pair_sentiment("EUR/USD", posts)
    print(f"  -> Pair: {sent_res.pair}")
    print(f"  -> Sentiment Label: {sent_res.sentiment_label}")
    print(f"  -> EUR Sentiment Score: {sent_res.base_sentiment}")
    print(f"  -> Discussion Volume: {sent_res.discussion_volume}")
    print(f"  -> Sources Count: {sent_res.source_count}")
    print("-------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(verify_intelligence())
