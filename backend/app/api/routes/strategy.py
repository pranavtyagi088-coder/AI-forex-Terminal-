import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import verify_api_token
from app.models.strategy import Strategy
from app.models.instrument import Instrument
from app.models.match_log import MatchScoreLog
from app.schemas.strategy import UseStrategyRequest, UseStrategyResponse
from app.engines.strategy.matching_engine import StrategyMatchingEngine, rank_strategies, score_strategy
from app.engines.strategy.market_state import MarketStateAnalyzer, build_market_state
from app.engines.strategy.trade_calculator import DeterministicTradeCalculator
from app.engines.strategy.mtf_validator import MultiTimeframeValidator
from app.engines.strategy.safety_gate import SafetyNoTradeGate
from app.services.market.data_service import MarketDataService, get_ohlcv_dataframe

router = APIRouter(prefix="/api/strategy", tags=["strategy"])

@router.get("/recommend")
async def recommend_strategies(
    symbol: str = Query(..., description="Instrument symbol, e.g. EUR/USD"),
    user_opt_in_grade_c: bool = Query(False, description="Allow Grade C strategies"),
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token)
):
    """Returns top 3 ranked strategies with template-filled why bullets."""
    inst_result = await db.execute(select(Instrument).where(Instrument.symbol == symbol))
    instrument = inst_result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {symbol} not found")

    strat_result = await db.execute(select(Strategy).where(Strategy.instrument_id == instrument.id))
    strategies = strat_result.scalars().all()
    if not strategies:
        raise HTTPException(status_code=404, detail=f"No strategies seeded for {symbol}")

    df = await get_ohlcv_dataframe(symbol, interval="1H", limit=100)
    market_state = build_market_state(df, symbol)
    ranked = rank_strategies(
        strategies=strategies,
        market_state=market_state,
        user_opt_in_grade_c=user_opt_in_grade_c
    )

    return {
        "symbol": symbol,
        "market_state": market_state.to_dict(),
        "recommendations": ranked
    }

@router.post("/use", response_model=UseStrategyResponse)
async def use_strategy(
    payload: UseStrategyRequest,
    db: AsyncSession = Depends(get_db),
    _token: str = Depends(verify_api_token)
):
    """
    14-Step 'USE THIS STRATEGY' Pipeline (Modules 4, 5, 6):
    Loads strategy, evaluates MTF alignment, computes deterministic entry/SL/TP/lots,
    runs safety gate, and logs execution to database.
    """
    # 1. Load Strategy
    strat_result = await db.execute(select(Strategy).where(Strategy.id == payload.strategy_id))
    strategy = strat_result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # 2. Load Instrument
    inst_result = await db.execute(select(Instrument).where(Instrument.symbol == payload.symbol))
    instrument = inst_result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {payload.symbol} not found")

    # 3. Fetch Multi-Timeframe Candles
    df_4h = await get_ohlcv_dataframe(payload.symbol, interval="4H", limit=60)
    df_1h = await get_ohlcv_dataframe(payload.symbol, interval="1H", limit=100)
    df_15m = await get_ohlcv_dataframe(payload.symbol, interval="15M", limit=60)

    # 4. Analyze MTF States
    htf_state = MarketStateAnalyzer.analyze(df_4h, payload.symbol)
    mtf_state = MarketStateAnalyzer.analyze(df_1h, payload.symbol)
    ltf_state = MarketStateAnalyzer.analyze(df_15m, payload.symbol)

    # 5. Determine Trade Direction
    direction = payload.direction
    if not direction:
        if "BULLISH" in mtf_state.get("regime", ""):
            direction = "BUY"
        elif "BEARISH" in mtf_state.get("regime", ""):
            direction = "SELL"
        else:
            direction = "BUY"

    # 6. Parse Strategy Rules
    rules = strategy.rules or {}
    if isinstance(rules, str):
        try:
            rules = json.loads(rules)
        except Exception:
            rules = {}

    # 7. Module 4: Calculate Deterministic Trade Parameters
    trade_calc = DeterministicTradeCalculator.calculate_trade(
        strategy_rules=rules,
        market_state=mtf_state,
        instrument=instrument,
        account_balance=payload.account_balance,
        risk_percent=payload.risk_percent,
        direction=direction,
        exchange_rate=1.0
    )

    # 8. Module 5: Multi-Timeframe Validator
    mtf_result = MultiTimeframeValidator.validate(
        htf_state=htf_state,
        mtf_state=mtf_state,
        ltf_state=ltf_state,
        direction=direction
    )

    # 9. Module 6: Safety Gate
    safety_result = SafetyNoTradeGate.evaluate(
        market_state=mtf_state,
        mtf_result=mtf_result,
        trade_calc=trade_calc,
        news_items=None,
        spread_pips=1.2,
        max_allowed_spread_pips=3.5
    )

    # 10. Prepare Trade Parameters Dict
    trade_params = {
        "direction": trade_calc.direction,
        "entry_price": trade_calc.entry_price,
        "stop_loss": trade_calc.stop_loss,
        "take_profit": trade_calc.take_profit,
        "stop_loss_pips": trade_calc.stop_loss_pips,
        "take_profit_pips": trade_calc.take_profit_pips,
        "risk_reward_ratio": trade_calc.risk_reward_ratio,
        "position_size_lots": trade_calc.position_size_lots,
        "risk_amount_usd": trade_calc.risk_amount_usd,
        "is_valid_rr": trade_calc.is_valid_rr
    }

    mtf_validation_dict = {
        "is_aligned": mtf_result.is_aligned,
        "decision": mtf_result.decision,
        "reasons": mtf_result.reasons,
        "htf_regime": mtf_result.htf_regime,
        "mtf_regime": mtf_result.mtf_regime,
        "ltf_regime": mtf_result.ltf_regime
    }

    # 11. Persist Execution Log to Database
    log_entry = MatchScoreLog(
        strategy_id=str(strategy.id),
        symbol=payload.symbol,
        decision=safety_result.decision,
        is_safe=safety_result.is_safe,
        match_score=85.0,
        blocking_reasons=safety_result.blocking_reasons,
        trade_parameters=trade_params,
        mtf_validation=mtf_validation_dict,
        market_state_snapshot=mtf_state
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)

    return UseStrategyResponse(
        strategy_id=str(strategy.id),
        strategy_name=strategy.name,
        symbol=payload.symbol,
        evidence_grade=strategy.evidence_grade,
        decision=safety_result.decision,
        is_safe=safety_result.is_safe,
        blocking_reasons=safety_result.blocking_reasons,
        trade_parameters=trade_params,
        mtf_validation=mtf_validation_dict,
        market_state_snapshot=mtf_state,
        log_id=log_entry.id
    )

