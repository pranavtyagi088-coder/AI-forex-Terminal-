from typing import List
from .base import SocialPost, SentimentResult

class FinancialSentimentEngine:
    """Calculates directional currency sentiment from collected posts & news"""
    
    BULLISH_WORDS = {"bullish", "buy", "breakout", "rally", "hawkish", "rate hike", "gains", "strong", "surge", "upside"}
    BEARISH_WORDS = {"bearish", "sell", "breakdown", "drop", "dovish", "rate cut", "losses", "weak", "plunge", "downside"}

    def analyze_post_sentiment(self, text: str) -> float:
        words = text.lower().split()
        score = 0.0
        for w in words:
            clean = w.strip(".,!?")
            if clean in self.BULLISH_WORDS:
                score += 0.2
            elif clean in self.BEARISH_WORDS:
                score -= 0.2
        return max(-1.0, min(1.0, score))

    def aggregate_pair_sentiment(self, pair: str, posts: List[SocialPost]) -> SentimentResult:
        parts = pair.split("/") if "/" in pair else [pair[:3], pair[3:]]
        base_curr = parts[0]
        quote_curr = parts[1] if len(parts) > 1 else "USD"
        
        if not posts:
            return SentimentResult(
                pair=pair, base_currency=base_curr, quote_currency=quote_curr,
                base_sentiment=0.0, quote_sentiment=0.0, pair_sentiment=0.0,
                sentiment_label="NEUTRAL", discussion_volume="LOW", source_count=0
            )

        total_score = 0.0
        weighted_count = 0.0
        
        for p in posts:
            p_score = self.analyze_post_sentiment(p.text)
            p.sentiment_score = p_score
            p.sentiment_label = "BULLISH" if p_score > 0.1 else ("BEARISH" if p_score < -0.1 else "NEUTRAL")
            
            weight = p.credibility_score
            total_score += (p_score * weight)
            weighted_count += weight

        avg_score = (total_score / weighted_count) if weighted_count > 0 else 0.0
        
        label = "NEUTRAL"
        if avg_score > 0.15:
            label = "BULLISH"
        elif avg_score < -0.15:
            label = "BEARISH"

        vol = "LOW" if len(posts) < 5 else ("MEDIUM" if len(posts) < 15 else "HIGH")

        return SentimentResult(
            pair=pair,
            base_currency=base_curr,
            quote_currency=quote_curr,
            base_sentiment=round(avg_score, 2),
            quote_sentiment=round(-avg_score, 2),  # Opposite currency reflection
            pair_sentiment=round(avg_score, 2),
            sentiment_label=label,
            discussion_volume=vol,
            source_count=len(posts)
        )
