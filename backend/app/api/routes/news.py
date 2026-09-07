"""News and Sentiment Stream API endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from app.core.auth import verify_api_token
from app.services.news.sentiment import fetch_latest_x_news

router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/latest")
async def get_latest_news(
    query: str = Query(default="forex OR USD OR EUR OR XAU OR BoJ"),
    limit: int = Query(default=10, ge=1, le=50),
    _token: str = Depends(verify_api_token),
):
    """Fetch latest macro breaking news, X / Twitter updates, and sentiment analysis."""
    news_items = await fetch_latest_x_news(query=query, limit=limit)
    return [
        {
            "id": item.id,
            "source": item.source,
            "author": item.author,
            "title": item.title,
            "content": item.content,
            "published_at": item.published_at.isoformat(),
            "sentiment": item.sentiment,
            "related_currencies": item.related_currencies,
            "impact_level": item.impact_level,
        }
        for item in news_items
    ]
