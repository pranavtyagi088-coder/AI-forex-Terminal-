"""Tests for Secure Upload and Market API routes."""

import io
import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_chart_upload_success():
    fake_image = io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRfake_png_binary_data")
    response = client.post(
        "/api/charts/upload",
        files={"file": ("chart_test.png", fake_image, "image/png")},
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "file_name" in data
    assert data["file_name"].endswith(".png")


def test_chart_upload_rejects_invalid_extension():
    fake_file = io.BytesIO(b"malicious executable payload")
    response = client.post(
        "/api/charts/upload",
        files={"file": ("exploit.exe", fake_file, "application/octet-stream")},
        headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_market_candles_endpoint_with_mock():
    mock_df = pd.DataFrame({
        "open": [1.1000, 1.1010],
        "high": [1.1020, 1.1030],
        "low": [1.0990, 1.1005],
        "close": [1.1010, 1.1025],
        "volume": [1000.0, 1200.0],
        "datetime": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"],
    })

    with patch("app.api.routes.market.get_ohlcv_dataframe", new=AsyncMock(return_value=mock_df)):
        response = client.get(
            "/api/market/candles?symbol=EUR/USD&timeframe=1H&bars=2",
            headers={"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "EUR/USD"
    assert data["bars_count"] == 2
    assert len(data["candles"]) == 2
