from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np


@dataclass
class MonteCarloConfidenceCone:
    percentile_5th: List[float]   # Pessimistic lower bound
    percentile_50th: List[float]  # Median trajectory
    percentile_95th: List[float]  # Optimistic upper bound


@dataclass
class MonteCarloSimulationResult:
    iterations_run: int
    trades_sampled_per_run: int
    median_final_equity: float
    pessimistic_5th_pct_equity: float
    optimistic_95th_pct_equity: float
    max_drawdown_95th_pct: float
    max_drawdown_99th_pct: float
    probability_of_ruin_pct: float  # Prob of hitting max drawdown limit
    is_prop_firm_safe: bool        # True if Prob of Ruin <= 1.0%
    confidence_cone: MonteCarloConfidenceCone
    ruin_threshold_used_pct: float


class MonteCarloEngine:
    """
    Institutional Monte Carlo Simulation & Risk of Ruin Engine (P3-#41 & #42).
    Runs 5,000+ bootstrap iterations to establish statistical drawdown confidence boundaries.
    """

    @classmethod
    def run_simulation(
        cls,
        trade_pnls: List[float],
        initial_capital: float = 100000.0,
        n_iterations: int = 5000,
        sample_horizon_trades: int = 100,
        max_drawdown_ruin_pct: float = 10.0,  # 10% Prop firm ruin limit
        random_seed: Optional[int] = 42,
    ) -> MonteCarloSimulationResult:
        if not trade_pnls or len(trade_pnls) < 5:
            # Fallback deterministic baseline if insufficient trades
            trade_pnls = [-500.0, 1000.0, -500.0, 1200.0, -400.0, 800.0]

        if random_seed is not None:
            np.random.seed(random_seed)

        pnls_array = np.array(trade_pnls, dtype=float)
        horizon = min(max(sample_horizon_trades, 20), 500)

        # Matrix bootstrap: (n_iterations, horizon)
        random_indices = np.random.randint(0, len(pnls_array), size=(n_iterations, horizon))
        sampled_pnl_matrix = pnls_array[random_indices]

        # Cumulative equity matrix
        equity_paths = initial_capital + np.cumsum(sampled_pnl_matrix, axis=1)
        initial_col = np.full((n_iterations, 1), initial_capital)
        equity_matrix = np.hstack([initial_col, equity_paths])

        # Compute running peaks and drawdowns
        running_peaks = np.maximum.accumulate(equity_matrix, axis=1)
        drawdowns_matrix = (running_peaks - equity_matrix) / running_peaks * 100.0
        max_drawdowns_per_run = np.max(drawdowns_matrix, axis=1)

        # Ruin Detection (Did max drawdown exceed ruin threshold?)
        ruin_events = np.sum(max_drawdowns_per_run >= max_drawdown_ruin_pct)
        prob_of_ruin = round(float((ruin_events / n_iterations) * 100.0), 2)

        # Percentile Metrics
        dd_95th = round(float(np.percentile(max_drawdowns_per_run, 95)), 2)
        dd_99th = round(float(np.percentile(max_drawdowns_per_run, 99)), 2)

        final_equities = equity_matrix[:, -1]
        median_final = round(float(np.median(final_equities)), 2)
        pessimistic_5th = round(float(np.percentile(final_equities, 5)), 2)
        optimistic_95th = round(float(np.percentile(final_equities, 95)), 2)

        # Sample equity curves for confidence cone (downsample to 20 steps for UI efficiency)
        step_indices = np.linspace(0, horizon, min(25, horizon + 1), dtype=int)
        cone_5th = [round(float(np.percentile(equity_matrix[:, step], 5)), 2) for step in step_indices]
        cone_50th = [round(float(np.percentile(equity_matrix[:, step], 50)), 2) for step in step_indices]
        cone_95th = [round(float(np.percentile(equity_matrix[:, step], 95)), 2) for step in step_indices]

        is_safe = prob_of_ruin <= 1.0 and dd_95th < max_drawdown_ruin_pct

        return MonteCarloSimulationResult(
            iterations_run=n_iterations,
            trades_sampled_per_run=horizon,
            median_final_equity=median_final,
            pessimistic_5th_pct_equity=pessimistic_5th,
            optimistic_95th_pct_equity=optimistic_95th,
            max_drawdown_95th_pct=dd_95th,
            max_drawdown_99th_pct=dd_99th,
            probability_of_ruin_pct=prob_of_ruin,
            is_prop_firm_safe=is_safe,
            confidence_cone=MonteCarloConfidenceCone(
                percentile_5th=cone_5th,
                percentile_50th=cone_50th,
                percentile_95th=cone_95th,
            ),
            ruin_threshold_used_pct=max_drawdown_ruin_pct,
        )
