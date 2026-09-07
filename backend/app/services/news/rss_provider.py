import httpx
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

@dataclass
class NewsArticle:
    title: str
    link: str
    pub_date: str
    source: str
    summary: str
    currencies: List[str]

class RSSNewsProvider:
    """Parses live official RSS feeds from Federal Reserve, ECB, and Bank of England"""
    
    FEEDS = {
        "ECB": ("https://www.ecb.europa.eu/rss/press.html", "EUR"),
        "FED": ("https://www.federalreserve.gov/feeds/press_all.xml", "USD"),
        "BOE": ("https://www.bankofengland.co.uk/rss/news", "GBP"),
    }

    async def fetch_latest_news(self, limit: int = 15) -> List[NewsArticle]:
        articles: List[NewsArticle] = []
        
        headers = {"User-Agent": "AIForexTerminal/3.0.0 (Institutional News Engine)"}
        
        async with httpx.AsyncClient(timeout=10.0, headers=headers, follow_redirects=True) as client:
            for source_name, (feed_url, currency) in self.FEEDS.items():
                try:
                    res = await client.get(feed_url)
                    if res.status_code == 200:
                        root = ET.fromstring(res.content)
                        items = root.findall(".//item")
                        
                        for item in items[:5]:
                            title = item.findtext("title") or "No Title"
                            link = item.findtext("link") or ""
                            pub_date = item.findtext("pubDate") or datetime.now(timezone.utc).isoformat()
                            desc = item.findtext("description") or ""
                            
                            articles.append(NewsArticle(
                                title=title.strip(),
                                link=link.strip(),
                                pub_date=pub_date.strip(),
                                source=source_name,
                                summary=desc.strip()[:250],
                                currencies=[currency]
                            ))
                except Exception as e:
                    logger.warning(f"Could not parse RSS for {source_name}: {e}")
                    
        return articles[:limit]
