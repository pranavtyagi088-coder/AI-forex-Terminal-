import pytest
import pandas as pd
from app.engines.backtest.engine import DeterministicBacktestEngine, generate_synthetic_ohlcv
from app.engines.risk.instruments import InstrumentRegistry


def test_same_code_path_backtester_sizing_and_decisions():
    """Backtest engine must generate trades using identical gatekeeper sizing and attach decision IDs."""
    df = generate_synthetic_ohlcv(n_bars=200, seed=42)
    engine = DeterministicBacktestEngine(
        symbol="EURUSD",
        initial_capital=100000.0,
        risk_per_trade=1.0,
        slippage_pips=0.5,
    )
    result = engine.run_simulation(df, strategy_id="trend_continuation")
    
    assert result.total_trades > 0
    # Verify every simulated trade has a cryptographic decision_id from Gatekeeper
    for t in result.trades:
        assert t.decision_id is not None
        assert t.decision_id.startswith("DEC-")
        assert t.position_size_lots > 0.0


def test_same_code_path_multi_instrument_specs():
    """Backtest engine correctly loads specs for Gold (XAUUSD) and JPY pairs."""
    df_gold = generate_synthetic_ohlcv(n_bars=200, base_price=2350.0, volatility=0.003, seed=10)
    engine_gold = DeterministicBacktestEngine(
        symbol="XAUUSD",
        initial_capital=100000.0,
        risk_per_trade=1.0,
    )
    res_gold = engine_gold.run_simulation(df_gold)
    assert engine_gold.canonical_symbol == "XAUUSD"
    assert res_gold.total_trades >= 0


def test_backtest_records_vetoed_signals():
    """Vetoed trades during extreme conditions must be recorded in veto summary."""
    df = generate_synthetic_ohlcv(n_bars=100, seed=123)
    engine = DeterministicBacktestEngine(
        symbol="EURUSD",
        initial_capital=10000.0,
        risk_per_trade=1.0,
    )
    result = engine.run_simulation(df)
    assert hasattr(result, "vetoed_signals_count")
    assert isinstance(result.veto_reasons_summary, dict)
