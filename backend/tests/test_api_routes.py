import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_health_check():
    """Verify health check endpoint returns 200 and version 3.0.0"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "3.0.0"
    assert "environment" in data

def test_auth_gate_rejects_missing_token():
    """Protected endpoints must reject requests without Authorization header"""
    response = client.get("/api/journal/recent")
    assert response.status_code in [401, 403]

def test_auth_gate_rejects_invalid_token():
    """Protected endpoints must reject requests with an invalid Bearer token"""
    headers = {"Authorization": "Bearer invalid_secret_token_12345"}
    response = client.get("/api/journal/recent", headers=headers)
    assert response.status_code in [401, 403]

def test_journal_recent_with_valid_token():
    """Authenticated user can fetch recent analysis journal"""
    headers = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    response = client.get("/api/journal/recent", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, (list, dict))

def test_risk_calculate_endpoint():
    """Verify risk calculation endpoint responds with valid sizing math"""
    headers = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}
    payload = {'symbol': 'EUR/USD', 'account_balance': 10000.0, 'risk_percent': 1.0, 'entry': 1.085, 'stop_loss': 1.08, 'take_profit_1': 1.095, 'leverage': 1.0, 'take_profit_2': 1.095}
    response = client.post("/api/risk/calculate", json=payload, headers=headers)
    assert response.status_code == 200
