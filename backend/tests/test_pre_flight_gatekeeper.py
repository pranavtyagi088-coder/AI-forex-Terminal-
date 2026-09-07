import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest
from app.engines.risk.correlation import OpenPositionInput

client = TestClient(app)


class TestPreFlightGatekeeper:
    def test_pre_flight_approved_clean_trade(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
        )
        res = engine.evaluate(req)
        assert res.allowed is True
        assert res.approved_lot_size > 0
        assert res.pip_risk == 50.0
        assert res.reward_risk_ratio == 2.0
        assert len(res.rejection_reasons) == 0
        assert res.gate_checks["circuit_breaker"] is True
        assert res.gate_checks["prop_firm_drawdown"] is True

    def test_pre_flight_blocked_by_circuit_breaker(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
            circuit_breaker_state="KILL_SWITCH",
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert res.approved_lot_size == 0.0
        assert any("KILL_SWITCH" in r for r in res.rejection_reasons)
        assert res.gate_checks["circuit_breaker"] is False

    def test_pre_flight_blocked_by_daily_drawdown(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="GBPUSD",
            direction="BUY",
            entry_price=1.2500,
            stop_loss=1.2450,
            account_balance=100000.0,
            current_daily_loss_pct=5.2,
            max_daily_loss_pct=5.0,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("Daily drawdown limit reached" in r for r in res.rejection_reasons)
        assert res.gate_checks["prop_firm_drawdown"] is False

    def test_pre_flight_blocked_by_news_blackout(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="SELL",
            entry_price=1.1000,
            stop_loss=1.1050,
            account_balance=100000.0,
            is_news_blackout=True,
            allow_news_trading=False,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("news blackout window" in r for r in res.rejection_reasons)
        assert res.gate_checks["news_and_calendar"] is False

    def test_pre_flight_blocked_by_cluster_overexposure(self):
        engine = PreFlightGatekeeper()
        open_trades = [
            OpenPositionInput(symbol="EURUSD", direction="BUY", risk_amount_usd=2000.0, risk_pct=2.0),
            OpenPositionInput(symbol="GBPUSD", direction="BUY", risk_amount_usd=2000.0, risk_pct=2.0),
            OpenPositionInput(symbol="AUDUSD", direction="BUY", risk_amount_usd=1000.0, risk_pct=1.0),
        ]
        req = PreFlightTradeRequest(
            symbol="NZDUSD",
            direction="BUY",
            entry_price=0.6000,
            stop_loss=0.5950,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
            open_positions=open_trades,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("CURRENCY_CLUSTER" in r or "MAX_PORTFOLIO_RISK" in r for r in res.rejection_reasons)
        assert res.gate_checks["portfolio_correlation"] is False

    def test_pre_flight_invalid_stop_loss_geometry(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.1050,  # Invalid: SL above entry on BUY
            account_balance=100000.0,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("Invalid Stop Loss geometry" in r for r in res.rejection_reasons)
        assert res.gate_checks["stop_loss_geometry"] is False

    def test_pre_flight_api_endpoint(self):
        payload = {
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100,
            "account_balance": 100000.0,
            "risk_per_trade_pct": 1.0,
            "circuit_breaker_state": "NORMAL",
            "current_daily_loss_pct": 0.5,
            "current_total_drawdown_pct": 1.0,
        }
        response = client.post("/api/trades/pre-flight-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["approved_lot_size"] > 0
        assert data["pip_risk"] == 50.0
        assert data["reward_risk_ratio"] == 2.0
