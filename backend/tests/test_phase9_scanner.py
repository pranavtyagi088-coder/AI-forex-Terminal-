import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal, init_db
from app.services.scanner.market_scanner import MarketScannerService


@pytest.mark.asyncio
async def test_market_scanner_service_scan_symbol():
    await init_db()
    async with AsyncSessionLocal() as session:
        candidate = await MarketScannerService.scan_symbol_timeframe(
            symbol="EUR/USD",
            timeframe="15",
            db=session
        )
        # Even if market is neutral or setup not high confluence, function returns cleanly (dict or None)
        assert candidate is None or isinstance(candidate, dict)
        if candidate:
            assert candidate["symbol"] == "EUR/USD"
            assert candidate["score"] >= 65.0
            assert candidate["direction"] in ["BUY", "SELL"]


@pytest.mark.asyncio
async def test_scanner_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test Scanner Status Endpoint
        res_status = await client.get("/api/scanner/status")
        assert res_status.status_code == 200
        status_data = res_status.json()
        assert status_data["status"] == "online"
        assert len(status_data["watchlist"]) >= 3

        # 2. Test Scan Now Endpoint
        res_scan = await client.post("/api/scanner/scan-now")
        assert res_scan.status_code == 200
        scan_data = res_scan.json()
        assert scan_data["status"] == "success"
        assert "signals" in scan_data

        # 3. Test Get Signals Endpoint
        res_signals = await client.get("/api/scanner/signals")
        assert res_signals.status_code == 200
        assert isinstance(res_signals.json(), list)
