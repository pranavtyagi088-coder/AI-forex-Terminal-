import pytest
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.engines.strategy.trade_calculator import DeterministicTradeCalculator
from app.engines.strategy.mtf_validator import MultiTimeframeValidator
from app.engines.strategy.safety_gate import SafetyNoTradeGate
from app.models.instrument import Instrument

client = TestClient(app)
AUTH_HEADERS = {"Authorization": f"Bearer {settings.API_AUTH_TOKEN}"}

def create_mock_instrument(symbol="EUR/USD", pip_size=0.0001, quote="USD"):
    return Instrument(
        symbol=symbol,
        pip_size=pip_size,
        contract_size=100000.0,
        base_currency="EUR",
        quote_currency=quote,
        active=True
    )

def test_trade_calculator_buy():
    inst = create_mock_instrument()
    rules = {
        "stop_conditions": {"atr_multiplier": 1.5},
        "take_profit_conditions": {"target_rr": 2.0},
        "min_acceptable_rr": 1.5
    }
    market_state = {"current_price": 1.0850, "atr": 0.0020}
    result = DeterministicTradeCalculator.calculate_trade(
        strategy_rules=rules,
        market_state=market_state,
        instrument=inst,
        account_balance=10000.0,
        risk_percent=1.0,
        direction="BUY"
    )
    assert result.direction == "BUY"
    assert result.entry_price == 1.0850
    assert result.stop_loss == 1.0820
    assert result.take_profit == 1.0910
    assert result.risk_reward_ratio == 2.0
    assert result.is_valid_rr is True
    assert result.position_size_lots > 0

def test_mtf_validator_blocks_opposing_htf():
    htf_state = {"regime": "TRENDING_BEARISH"}
    mtf_state = {"regime": "TRENDING_BULLISH", "is_choppy": False}
    ltf_state = {"regime": "TRENDING_BULLISH", "rsi": 55.0}

    res = MultiTimeframeValidator.validate(htf_state, mtf_state, ltf_state, direction="BUY")
    assert res.is_aligned is False
    assert res.decision == "NO_TRADE"
    assert any("HTF trend conflict" in r for r in res.reasons)

def test_safety_gate_extreme_volatility():
    inst = create_mock_instrument()
    rules = {"stop_conditions": {"atr_multiplier": 1.5}, "take_profit_conditions": {"target_rr": 2.0}}
    market_state = {"current_price": 1.0850, "atr": 0.0020, "volatility_percentile": 98.0}
    
    trade = DeterministicTradeCalculator.calculate_trade(
        strategy_rules=rules,
        market_state=market_state,
        instrument=inst,
        account_balance=10000.0,
        risk_percent=1.0,
        direction="BUY"
    )
    
    mtf_res = MultiTimeframeValidator.validate(
        {"regime": "TRENDING_BULLISH"},
        {"regime": "TRENDING_BULLISH", "is_choppy": False},
        {"regime": "TRENDING_BULLISH", "rsi": 50.0},
        "BUY"
    )

    safety = SafetyNoTradeGate.evaluate(market_state, mtf_res, trade)
    assert safety.decision == "NO_TRADE"
    assert safety.is_safe is False
    assert any("Extreme volatility spike" in r for r in safety.blocking_reasons)

def test_use_strategy_api_pipeline():
    # 1. Get strategies for EUR/USD
    rec_res = client.get("/api/strategy/recommend?symbol=EUR/USD", headers=AUTH_HEADERS)
    assert rec_res.status_code == 200
    data = rec_res.json()
    assert len(data["recommendations"]) > 0
    strategy_id = data["recommendations"][0]["strategy_id"]

    # 2. Call /api/strategy/use
    use_res = client.post(
        "/api/strategy/use",
        headers=AUTH_HEADERS,
        json={
            "strategy_id": str(strategy_id),
            "symbol": "EUR/USD",
            "account_balance": 25000.0,
            "risk_percent": 1.0
        }
    )
    assert use_res.status_code == 200
    res_data = use_res.json()
    assert str(res_data["strategy_id"]) == str(strategy_id)
    assert res_data["symbol"] == "EUR/USD"
    assert res_data["decision"] in ["TRADE", "WAIT", "NO_TRADE"]
    assert res_data["trade_parameters"]["position_size_lots"] > 0
    assert "log_id" in res_data
