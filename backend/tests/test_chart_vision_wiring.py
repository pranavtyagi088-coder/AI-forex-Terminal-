import asyncio
import os
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db

def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def test_analysis_run_with_chart_image():
    async def run():
        await init_db()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            os.makedirs("uploads", exist_ok=True)
            dummy_chart = os.path.join("uploads", "sample_chart_test.png")
            with open(dummy_chart, "w") as f:
                f.write("fake_image_bytes")

            payload = {
                "symbol": "EURUSD",
                "timeframe": "15",
                "direction": "BUY",
                "imagePaths": [dummy_chart],
                "accountBalance": 100000.0,
                "riskPercent": 1.0
            }
            response = await client.post("/api/analysis/run", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "EURUSD"
            assert data["timeframe"] == "15"
            assert data["confidence"] >= 0.80
            assert dummy_chart in data["chartImages"]

            if os.path.exists(dummy_chart):
                os.remove(dummy_chart)
    run_async(run())
