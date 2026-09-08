from __future__ import annotations

import io
import json
import math
from typing import Optional, List, Dict, Any
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.backtest import BacktestRun
from app.schemas.backtest import (
    BacktestRequest,
    BacktestResponse,
    BacktestMetrics,
    TradeLogItem,
    StrategyComparisonResponse,
    StrategyComparisonItem,
    WalkForwardMetricsSchema,
)
from app.engines.backtest.engine import (
    DeterministicBacktestEngine,
    generate_synthetic_ohlcv,
    BacktestResult,
)
from app.engines.backtest.walk_forward import WalkForwardValidator, WalkForwardMetrics

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


def _result_to_response(
    result: BacktestResult,
    req: BacktestRequest,
    data_source: str = "synthetic",
    is_result: Optional[BacktestResult] = None,
    oos_result: Optional[BacktestResult] = None,
    wfe_metrics: Optional[WalkForwardMetrics] = None,
    total_bars: int = 500,
    notes: Optional[List[str]] = None,
) -> BacktestResponse:
    metrics = BacktestMetrics(
        total_trades=int(result.total_trades),
        winning_trades=int(result.winning_trades),
        losing_trades=int(result.losing_trades),
        win_rate=float(result.win_rate),
        profit_factor=float(result.profit_factor),
        expectancy_r=float(result.expectancy_r),
        expectancy_usd=float(result.expectancy_usd),
        max_drawdown=float(result.max_drawdown),
        max_drawdown_pct=float(result.max_drawdown_pct),
        net_profit=float(result.net_profit),
        net_profit_pct=float(result.net_profit_pct),
        sharpe_ratio=float(result.sharpe_ratio),
        avg_rr=float(result.avg_rr),
        consecutive_losses=int(result.consecutive_losses),
        total_bars=int(result.total_bars),
    )

    is_metrics = None
    if is_result:
        is_metrics = BacktestMetrics(
            total_trades=int(is_result.total_trades),
            winning_trades=int(is_result.winning_trades),
            losing_trades=int(is_result.losing_trades),
            win_rate=float(is_result.win_rate),
            profit_factor=float(is_result.profit_factor),
            expectancy_r=float(is_result.expectancy_r),
            expectancy_usd=float(is_result.expectancy_usd),
            max_drawdown=float(is_result.max_drawdown),
            max_drawdown_pct=float(is_result.max_drawdown_pct),
            net_profit=float(is_result.net_profit),
            net_profit_pct=float(is_result.net_profit_pct),
            sharpe_ratio=float(is_result.sharpe_ratio),
            avg_rr=float(is_result.avg_rr),
            consecutive_losses=int(is_result.consecutive_losses),
            total_bars=int(is_result.total_bars),
        )

    oos_metrics = None
    if oos_result:
        oos_metrics = BacktestMetrics(
            total_trades=int(oos_result.total_trades),
            winning_trades=int(oos_result.winning_trades),
            losing_trades=int(oos_result.losing_trades),
            win_rate=float(oos_result.win_rate),
            profit_factor=float(oos_result.profit_factor),
            expectancy_r=float(oos_result.expectancy_r),
            expectancy_usd=float(oos_result.expectancy_usd),
            max_drawdown=float(oos_result.max_drawdown),
            max_drawdown_pct=float(oos_result.max_drawdown_pct),
            net_profit=float(oos_result.net_profit),
            net_profit_pct=float(oos_result.net_profit_pct),
            sharpe_ratio=float(oos_result.sharpe_ratio),
            avg_rr=float(oos_result.avg_rr),
            consecutive_losses=int(oos_result.consecutive_losses),
            total_bars=int(oos_result.total_bars),
        )

    wfe_schema = None
    if wfe_metrics:
        wfe_schema = WalkForwardMetricsSchema(
            wfe_score_pct=float(wfe_metrics.wfe_score_pct),
            profit_factor_retention_pct=float(wfe_metrics.profit_factor_retention_pct),
            win_rate_decay_pct=float(wfe_metrics.win_rate_decay_pct),
            drawdown_expansion_ratio=float(wfe_metrics.drawdown_expansion_ratio),
            is_overfit_suspect=bool(wfe_metrics.is_overfit_suspect),
            robustness_grade=str(wfe_metrics.robustness_grade),
            verdict_summary=str(wfe_metrics.verdict_summary),
            details=wfe_metrics.details,
        )

    trade_log = [
        TradeLogItem(
            entry_bar=int(t.entry_bar),
            exit_bar=int(t.exit_bar),
            direction=str(t.direction),
            entry_price=float(t.entry_price),
            exit_price=float(t.exit_price),
            pnl=float(t.pnl),
            pnl_pct=float(t.pnl_pct),
            r_multiple=float(t.r_multiple),
            exit_reason=str(t.exit_reason),
        )
        for t in result.trades
    ]

    return BacktestResponse(
        status="success",
        symbol=req.symbol,
        timeframe=req.timeframe,
        strategy=req.strategy,
        metrics=metrics,
        trade_log=trade_log,
        equity_curve=result.equity_curve,
        drawdown_curve=result.drawdown_curve,
        is_metrics=is_metrics,
        oos_metrics=oos_metrics,
        walk_forward_metrics=wfe_schema,
        data_source=data_source,
        slippage_pips_used=req.slippage_pips,
        commission_per_lot_used=req.commission_per_lot,
        bars_analyzed=total_bars,
        notes=notes or ["Simulation completed successfully."],
        overall_metrics=metrics,
        in_sample_metrics=is_metrics,
        out_of_sample_metrics=oos_metrics,
    )


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest, db: AsyncSession = Depends(get_db)):
    try:
        bars = req.bars_count if req.bars_count is not None else 500

        df = generate_synthetic_ohlcv(
            n_bars=bars,
            base_price=1.1000 if "JPY" not in req.symbol else 150.0,
            volatility=0.002,
            seed=req.random_seed,
        )

        engine = DeterministicBacktestEngine(
            initial_capital=req.initial_capital,
            risk_per_trade=req.risk_per_trade,
            slippage_pips=req.slippage_pips,
            commission_per_lot=req.commission_per_lot,
            symbol=req.symbol,
        )

        split_idx = int(len(df) * 0.7)
        df_is = df.iloc[:split_idx].reset_index(drop=True)
        df_oos = df.iloc[split_idx:].reset_index(drop=True)

        full_result = engine.run_simulation(df, strategy_id=req.strategy)
        is_result = engine.run_simulation(df_is, strategy_id=req.strategy)
        oos_result = engine.run_simulation(df_oos, strategy_id=req.strategy)

        wfe_metrics = WalkForwardValidator.evaluate_is_oos(is_result, oos_result)

        try:
            pf_val = float(full_result.profit_factor)
            if np.isinf(pf_val) or np.isnan(pf_val):
                pf_val = 99.0

            run_record = BacktestRun(
                symbol=req.symbol,
                timeframe=req.timeframe,
                initial_balance=float(req.initial_capital),
                final_balance=float(full_result.equity_curve[-1]) if full_result.equity_curve else float(req.initial_capital),
                net_profit=float(full_result.net_profit),
                win_rate=float(full_result.win_rate),
                profit_factor=pf_val,
                max_drawdown=float(full_result.max_drawdown_pct),
                sharpe_ratio=float(full_result.sharpe_ratio),
                total_trades=int(full_result.total_trades),
                metrics_json={
                    "wfe_score_pct": float(wfe_metrics.wfe_score_pct),
                    "robustness_grade": str(wfe_metrics.robustness_grade),
                    "is_overfit_suspect": bool(wfe_metrics.is_overfit_suspect),
                },
            )
            db.add(run_record)
            await db.commit()
        except Exception:
            pass

        return _result_to_response(
            full_result,
            req,
            data_source="synthetic",
            is_result=is_result,
            oos_result=oos_result,
            wfe_metrics=wfe_metrics,
            total_bars=bars,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Backtest execution failure: {str(e)}")


@router.post("/run-csv", response_model=BacktestResponse)
async def run_backtest_csv(
    file: UploadFile = File(...),
    symbol: str = Form("EUR/USD"),
    timeframe: str = Form("1h"),
    strategy: str = Form("trend_continuation"),
    strategy_name: Optional[str] = Form(None),
    initial_capital: float = Form(10000.0),
    initial_balance: Optional[float] = Form(None),
    risk_per_trade: float = Form(1.0),
    risk_percent: Optional[float] = Form(None),
    slippage_pips: float = Form(0.5),
    commission_per_lot: float = Form(7.0),
    split_oos: Optional[bool] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        contents = await file.read()
        if len(contents) > 25 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large (max 25MB)")

        actual_capital = initial_balance if initial_balance is not None else initial_capital
        actual_risk = risk_percent if risk_percent is not None else risk_per_trade
        actual_strategy = "trend_continuation"

        try:
            df = pd.read_csv(io.BytesIO(contents))
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid CSV format")

        if len(df) == 0:
            raise HTTPException(status_code=400, detail="CSV is empty")

        col_map = {c.lower().strip(): c for c in df.columns}
        required = ["open", "high", "low", "close"]
        for r in required:
            if r not in col_map:
                raise HTTPException(status_code=400, detail=f"Missing mandatory column: {r}")

        df = df.rename(columns={col_map[r]: r for r in required if r in col_map})

        if "time" in col_map and "date" in col_map:
            df["timestamp"] = pd.to_datetime(df[col_map["date"]].astype(str) + " " + df[col_map["time"]].astype(str), errors="coerce")
        elif "timestamp" in col_map:
            df["timestamp"] = pd.to_datetime(df[col_map["timestamp"]], errors="coerce")
        elif "date" in col_map:
            df["timestamp"] = pd.to_datetime(df[col_map["date"]], errors="coerce")
        else:
            df["timestamp"] = pd.date_range("2024-01-01", periods=len(df), freq="1h")

        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df.drop_duplicates(subset=["timestamp"])
        df = df.sort_values("timestamp").reset_index(drop=True)

        if len(df) < 20:
            raise HTTPException(status_code=400, detail=f"Minimum 20 bars required, got {len(df)}")

        engine = DeterministicBacktestEngine(
            initial_capital=actual_capital,
            risk_per_trade=actual_risk,
            slippage_pips=slippage_pips,
            commission_per_lot=commission_per_lot,
            symbol=symbol,
        )

        req = BacktestRequest(
            symbol=symbol,
            timeframe=timeframe,
            strategy=actual_strategy,
            initial_capital=actual_capital,
            risk_per_trade=actual_risk,
            slippage_pips=slippage_pips,
            commission_per_lot=commission_per_lot,
        )

        split_idx = int(len(df) * 0.7)
        df_is = df.iloc[:split_idx].reset_index(drop=True)
        df_oos = df.iloc[split_idx:].reset_index(drop=True)

        full_result = engine.run_simulation(df, strategy_id=actual_strategy)

        is_result = None
        oos_result = None
        wfe_metrics = None
        if len(df) >= 50:
            is_result = engine.run_simulation(df_is, strategy_id=actual_strategy)
            oos_result = engine.run_simulation(df_oos, strategy_id=actual_strategy)
            wfe_metrics = WalkForwardValidator.evaluate_is_oos(is_result, oos_result)

        resp = _result_to_response(
            full_result,
            req,
            data_source="csv",
            is_result=is_result,
            oos_result=oos_result,
            wfe_metrics=wfe_metrics,
            total_bars=len(df),
            notes=["Custom CSV Ingested: Full dataset validated and processed."],
        )
        return resp

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/compare", response_model=StrategyComparisonResponse)
async def compare_strategies(req: BacktestRequest):
    strategies_to_compare = req.compare_strategies or ["trend_continuation", "mean_reversion"]
    bars = req.bars_count if req.bars_count is not None else 500

    df = generate_synthetic_ohlcv(
        n_bars=bars,
        base_price=1.1000 if "JPY" not in req.symbol else 150.0,
        volatility=0.002,
        seed=req.random_seed or 42,
    )

    engine = DeterministicBacktestEngine(
        initial_capital=req.initial_capital,
        risk_per_trade=req.risk_per_trade,
        slippage_pips=req.slippage_pips,
        commission_per_lot=req.commission_per_lot,
        symbol=req.symbol,
    )

    comparisons = []
    for strat in strategies_to_compare:
        result = engine.run_simulation(df, strategy_id=strat)
        metrics = BacktestMetrics(
            total_trades=int(result.total_trades),
            winning_trades=int(result.winning_trades),
            losing_trades=int(result.losing_trades),
            win_rate=float(result.win_rate),
            profit_factor=float(result.profit_factor),
            expectancy_r=float(result.expectancy_r),
            expectancy_usd=float(result.expectancy_usd),
            max_drawdown=float(result.max_drawdown),
            max_drawdown_pct=float(result.max_drawdown_pct),
            net_profit=float(result.net_profit),
            net_profit_pct=float(result.net_profit_pct),
            sharpe_ratio=float(result.sharpe_ratio),
            avg_rr=float(result.avg_rr),
            consecutive_losses=int(result.consecutive_losses),
            total_bars=int(result.total_bars),
        )
        comparisons.append(StrategyComparisonItem(
            strategy=strat,
            metrics=metrics,
            equity_curve=result.equity_curve,
            drawdown_curve=result.drawdown_curve,
        ))

    return StrategyComparisonResponse(
        status="success",
        symbol=req.symbol,
        timeframe=req.timeframe,
        data_source="synthetic",
        total_bars=bars,
        comparisons=comparisons,
    )


@router.get("/history")
async def get_backtest_history(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(20))
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "timeframe": r.timeframe,
            "initial_balance": r.initial_balance,
            "final_balance": r.final_balance,
            "net_profit": r.net_profit,
            "win_rate": r.win_rate,
            "profit_factor": r.profit_factor,
            "max_drawdown": r.max_drawdown,
            "total_trades": r.total_trades,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "metrics": r.metrics_json or {},
        }
        for r in runs
    ]
