import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.engines.risk.gatekeeper import PreFlightGatekeeper, PreFlightTradeRequest
from app.engines.risk.correlation import OpenPositionInput

client = TestClient(app)


class TestPreFlightGatekeeper:
    def test_pre_flight_approved_clean_trade(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD.pro",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            take_profit=1.1100,
            account_balance=100000.0,
            risk_per_trade_pct=1.0,
        )
        res = engine.evaluate(req)
        assert res.allowed is True
        assert res.canonical_symbol == "EURUSD"
        assert res.approved_lot_size > 0
        assert res.pip_risk == 50.0
        assert res.reward_risk_ratio == 2.0
        assert len(res.rejection_reasons) == 0
        assert res.gate_checks["instrument_supported"] is True

    def test_pre_flight_freshness_gate_blocks_stale_account(self):
        engine = PreFlightGatekeeper()
        stale_time = datetime.now(timezone.utc) - timedelta(seconds=180)  # 3 minutes stale
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
            account_last_synced_at=stale_time,
            require_fresh_account_data=True,
            freshness_threshold_seconds=60,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("STALE_ACCOUNT_DATA" in r for r in res.rejection_reasons)
        assert res.gate_checks["account_freshness"] is False

    def test_pre_flight_spread_guard_rejection(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
            current_spread_pips=4.2,  # Limit is 2.5 pips
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("SPREAD_EXCEEDS_MAX_LIMIT" in r for r in res.rejection_reasons)
        assert res.gate_checks["spread_guard"] is False

    def test_pre_flight_unsupported_instrument_fails_closed(self):
        engine = PreFlightGatekeeper()
        req = PreFlightTradeRequest(
            symbol="RANDOMPAIR123",
            direction="BUY",
            entry_price=1.1000,
            stop_loss=1.0950,
            account_balance=100000.0,
        )
        res = engine.evaluate(req)
        assert res.allowed is False
        assert any("UNSUPPORTED_INSTRUMENT" in r for r in res.rejection_reasons)
        assert res.gate_checks["instrument_supported"] is False

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
            stop_loss=1.1050,
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
        assert data["canonical_symbol"] == "EURUSD"
        assert data["approved_lot_size"] > 0
        assert data["pip_risk"] == 50.0
        assert data["reward_risk_ratio"] == 2.0
