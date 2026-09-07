from typing import Protocol, List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class SocialPost:
    id: str
    provider: str  # "reddit" | "rss" | "x" | "official"
    author: str
    text: str
    published_at: str
    url: Optional[str] = None
    currencies: List[str] = field(default_factory=list)
    pairs: List[str] = field(default_factory=list)
    sentiment_label: str = "NEUTRAL"  # BULLISH | BEARISH | NEUTRAL | MIXED
    sentiment_score: float = 0.0      # -1.0 to 1.0
    credibility_score: float = 0.5    # 0.0 to 1.0

@dataclass
class SentimentResult:
    pair: str
    base_currency: str
    quote_currency: str
    base_sentiment: float
    quote_sentiment: float
    pair_sentiment: float
    sentiment_label: str
    discussion_volume: str            # "LOW" | "MEDIUM" | "HIGH"
    top_narratives: List[str] = field(default_factory=list)
    source_count: int = 0

class SocialIntelligenceProvider(Protocol):
    """Universal Interface for all social/discussion sources"""
    
    async def fetch_posts(self, pair: str, limit: int = 20) -> List[SocialPost]:
        ...
        
    async def get_provider_health(self) -> Dict[str, Any]:
        ...
