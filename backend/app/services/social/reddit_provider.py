import httpx
import logging
from typing import List, Dict, Any
from datetime import datetime
from .base import SocialIntelligenceProvider, SocialPost

logger = logging.getLogger(__name__)

class RedditSocialProvider(SocialIntelligenceProvider):
    """Fetches public Forex community discussions from Reddit without requiring API keys"""
    
    SUBREDDITS = ["Forex", "Economics", "WallStreetBets"]
    
    async def fetch_posts(self, pair: str, limit: int = 20) -> List[SocialPost]:
        clean_pair = pair.replace("/", "").upper()
        base_curr = pair.split("/")[0] if "/" in pair else pair[:3]
        posts: List[SocialPost] = []
        
        headers = {"User-Agent": "AIForexTerminal/3.0.0 (Financial Intelligence Terminal)"}
        
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            for sub in self.SUBREDDITS:
                url = f"https://www.reddit.com/r/{sub}/search.json?q={clean_pair}&sort=new&limit=5"
                try:
                    res = await client.get(url)
                    if res.status_code == 200:
                        data = res.json()
                        children = data.get("data", {}).get("children", [])
                        for child in children:
                            pdata = child.get("data", {})
                            title = pdata.get("title", "")
                            selftext = pdata.get("selftext", "")
                            full_text = f"{title}. {selftext[:200]}"
                            
                            posts.append(SocialPost(
                                id=f"reddit_{pdata.get('id', '')}",
                                provider="reddit",
                                author=pdata.get("author", "anonymous"),
                                text=full_text,
                                published_at=datetime.utcfromtimestamp(pdata.get("created_utc", 0)).isoformat(),
                                url=f"https://reddit.com{pdata.get('permalink', '')}",
                                currencies=[base_curr],
                                pairs=[pair],
                                credibility_score=0.45  # Default weight for trading communities
                            ))
                except Exception as e:
                    logger.warning(f"Reddit provider error for r/{sub}: {e}")
                    
        return posts[:limit]

    async def get_provider_health(self) -> Dict[str, Any]:
        return {"provider": "reddit", "status": "ACTIVE", "type": "public_json"}
