"""Tests for News and X sentiment engine."""

import pytest
from fastapi.testclient import TestClient
from app.core.config import settings
from app.main import app
from app.services.news.sentiment import classify_headline_risk

client = TestClient(app)


def test_classify_headline_risk_keywords():
    sentiment, impact = classify_headline_risk("Fed announces unexpected 50bp rate hike")
    assert impact == "HIGH"
    assert sentiment == "BULLISH"

    sentiment, impact = classify_headline_risk("Central Bank prepares emergency rate cut amid recession fears")
    assert impact == "HIGH"
    assert sentiment == "BEARISH"


def test_news_endpoint_returns_items():
    response = client.get(
        "/api/news/latest?limit=5",
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "source" in data[0]
    assert "sentiment" in data[0]
    assert "impact_level" in data[0]
