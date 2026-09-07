from dataclasses import dataclass, field
from typing import List, Dict, Any
from .rss_provider import RSSNewsProvider, NewsArticle

@dataclass
class MacroContext:
    pair: str
    news_risk_level: str  # "LOW" | "MEDIUM" | "HIGH" | "EXTREME"
    high_impact_news_count: int
    articles: List[NewsArticle] = field(default_factory=list)
    summary: str = ""

class NewsImpactEngine:
    """Evaluates macro news risks and impact levels for specific currency pairs"""

    HIGH_IMPACT_KEYWORDS = {
        "cpi", "nfp", "fomc", "interest rate", "inflation", "gdp",
        "unemployment", "payroll", "ecb press conference", "hawkish", "dovish",
        "monetary policy", "rate hike", "rate cut"
    }

    def __init__(self):
        self.rss_provider = RSSNewsProvider()

    def calculate_article_impact(self, title: str, summary: str) -> str:
        combined = f"{title} {summary}".lower()
        for kw in self.HIGH_IMPACT_KEYWORDS:
            if kw in combined:
                return "HIGH"
        return "MEDIUM" if len(combined) > 60 else "LOW"

    async def get_macro_context(self, pair: str) -> MacroContext:
        parts = pair.split("/") if "/" in pair else [pair[:3], pair[3:]]
        base_curr = parts[0]
        quote_curr = parts[1] if len(parts) > 1 else "USD"

        all_articles = await self.rss_provider.fetch_latest_news(limit=20)
        
        # Filter news for relevant currencies in the pair
        relevant = [
            a for a in all_articles 
            if base_curr in a.currencies or quote_curr in a.currencies or "USD" in a.currencies
        ]

        high_impact_count = 0
        for a in relevant:
            impact = self.calculate_article_impact(a.title, a.summary)
            if impact == "HIGH":
                high_impact_count += 1

        risk_level = "LOW"
        if high_impact_count >= 3:
            risk_level = "HIGH"
        elif high_impact_count >= 1:
            risk_level = "MEDIUM"

        summary = (
            f"Macro news risk for {pair} evaluated as {risk_level}. "
            f"Identified {len(relevant)} central bank releases "
            f"({high_impact_count} high-impact macroeconomic drivers)."
        )

        return MacroContext(
            pair=pair,
            news_risk_level=risk_level,
            high_impact_news_count=high_impact_count,
            articles=relevant,
            summary=summary
        )
