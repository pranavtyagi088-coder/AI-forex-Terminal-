from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from app.engines.backtest.engine import DeterministicBacktestEngine, BacktestResult


@dataclass
class WalkForwardMetrics:
    wfe_score_pct: float
    profit_factor_retention_pct: float
    win_rate_decay_pct: float
    drawdown_expansion_ratio: float
    is_overfit_suspect: bool
    robustness_grade: str  # "ROBUST", "ACCEPTABLE", "FRAGILE", "OVERFIT"
    verdict_summary: str
    details: Dict[str, Any]


@dataclass
class RollingWindowResult:
    window_index: int
    train_bars: int
    test_bars: int
    is_profit_factor: float
    oos_profit_factor: float
    is_win_rate: float
    oos_win_rate: float
    window_wfe_pct: float


class WalkForwardValidator:
    """
    Institutional Walk-Forward Optimization & Out-of-Sample Validation Engine (P1-#23 & #24).
    Mathematically detects curve-fitting and evaluates strategy persistence on unseen market regimes.
    """

    @classmethod
    def evaluate_is_oos(
        cls,
        is_result: BacktestResult,
        oos_result: BacktestResult,
    ) -> WalkForwardMetrics:
        """Calculate Walk-Forward Efficiency (WFE) and robustness grading between IS and OOS runs."""
        is_pf = max(0.01, is_result.profit_factor if not math_is_infinite(is_result.profit_factor) else 5.0)
        oos_pf = max(0.0, oos_result.profit_factor if not math_is_infinite(oos_result.profit_factor) else 5.0)

        is_exp_r = is_result.expectancy_r
        oos_exp_r = oos_result.expectancy_r

        is_wr = is_result.win_rate
        oos_wr = oos_result.win_rate

        is_dd = max(0.1, is_result.max_drawdown_pct)
        oos_dd = max(0.1, oos_result.max_drawdown_pct)

        # 1. Core Metric Formulas
        pf_retention = round((oos_pf / is_pf) * 100.0, 2)
        wr_decay = round(is_wr - oos_wr, 2)
        dd_expansion = round(oos_dd / is_dd, 2)

        # WFE Score: Expectancy retention if positive, otherwise clamped
        if is_exp_r > 0:
            raw_wfe = (oos_exp_r / is_exp_r) * 100.0
            wfe_score = round(max(0.0, min(raw_wfe, 150.0)), 2)
        else:
            wfe_score = 0.0 if oos_exp_r <= 0 else 50.0

        # 2. Institutional Robustness Grading
        is_overfit = False
        if oos_exp_r <= 0 or wfe_score < 35.0 or pf_retention < 40.0:
            grade = "OVERFIT"
            is_overfit = True
            summary = "CRITICAL: Strategy failed out-of-sample validation. Severe curve-fitting detected."
        elif wfe_score < 50.0 or wr_decay > 15.0 or dd_expansion > 2.0:
            grade = "FRAGILE"
            is_overfit = True
            summary = "WARNING: Strategy shows elevated decay in out-of-sample testing."
        elif wfe_score < 65.0 or pf_retention < 70.0:
            grade = "ACCEPTABLE"
            summary = "MODERATE: Strategy exhibits acceptable efficiency on unseen data."
        else:
            grade = "ROBUST"
            summary = "INSTITUTIONAL GRADE: Strategy demonstrates high statistical persistence across regimes."

        return WalkForwardMetrics(
            wfe_score_pct=wfe_score,
            profit_factor_retention_pct=pf_retention,
            win_rate_decay_pct=wr_decay,
            drawdown_expansion_ratio=dd_expansion,
            is_overfit_suspect=is_overfit,
            robustness_grade=grade,
            verdict_summary=summary,
            details={
                "is_profit_factor": is_pf,
                "oos_profit_factor": oos_pf,
                "is_win_rate": is_wr,
                "oos_win_rate": oos_wr,
                "is_expectancy_r": is_exp_r,
                "oos_expectancy_r": oos_exp_r,
                "is_max_dd_pct": is_dd,
                "oos_max_dd_pct": oos_dd,
            },
        )

    @classmethod
    def run_rolling_walk_forward(
        cls,
        df: pd.DataFrame,
        engine: DeterministicBacktestEngine,
        strategy_id: str = "trend_continuation",
        n_windows: int = 3,
        train_ratio: float = 0.7,
    ) -> List[RollingWindowResult]:
        """Execute multi-window rolling Walk-Forward analysis across temporal slices."""
        n_bars = len(df)
        if n_bars < 150:
            return []

        window_size = n_bars // n_windows
        results = []

        for w in range(n_windows):
            start_idx = w * window_size
            end_idx = start_idx + window_size if w < n_windows - 1 else n_bars
            sub_df = df.iloc[start_idx:end_idx].reset_index(drop=True)

            if len(sub_df) < 50:
                continue

            split_pt = int(len(sub_df) * train_ratio)
            df_train = sub_df.iloc[:split_pt].reset_index(drop=True)
            df_test = sub_df.iloc[split_pt:].reset_index(drop=True)

            if len(df_train) < 30 or len(df_test) < 20:
                continue

            try:
                res_train = engine.run_simulation(df_train, strategy_id=strategy_id)
                res_test = engine.run_simulation(df_test, strategy_id=strategy_id)

                wfe_meta = cls.evaluate_is_oos(res_train, res_test)
                results.append(RollingWindowResult(
                    window_index=w + 1,
                    train_bars=len(df_train),
                    test_bars=len(df_test),
                    is_profit_factor=res_train.profit_factor,
                    oos_profit_factor=res_test.profit_factor,
                    is_win_rate=res_train.win_rate,
                    oos_win_rate=res_test.win_rate,
                    window_wfe_pct=wfe_meta.wfe_score_pct,
                ))
            except Exception:
                continue

        return results


def math_is_infinite(val: float) -> bool:
    return np.isinf(val) or val >= 999.0
