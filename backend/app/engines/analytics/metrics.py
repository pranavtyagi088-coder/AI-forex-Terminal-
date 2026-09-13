from __future__ import annotations
import math
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class RollingPerformanceMetrics(BaseModel):
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate_pct: float = 0.0
    profit_factor: float = 0.0
    expectancy_usd: float = 0.0
    average_r_multiple: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    consecutive_losses_max: int = 0
    total_pnl_usd: float = 0.0
    is_statistically_significant: bool = False


class SlippagePostMortem(BaseModel):
    total_analyzed_trades: int = 0
    average_slippage_pips: float = 0.0
    max_adverse_slippage_pips: float = 0.0
    adverse_execution_rate_pct: float = 0.0
    favorable_execution_rate_pct: float = 0.0
    zero_slippage_rate_pct: float = 0.0
    total_slippage_cost_usd: float = 0.0
    execution_quality_score: float = 100.0  # 0 to 100 scale


class QuantitativeAnalyticsEngine:
    """Institutional Grade Quantitative Risk and Performance Engine."""

    @staticmethod
    def calculate_rolling_metrics(
        pnls: List[float],
        r_multiples: Optional[List[float]] = None,
        risk_free_rate_annual: float = 0.02,
        initial_balance: float = 100000.0,
    ) -> RollingPerformanceMetrics:
        n = len(pnls)
        if n == 0:
            return RollingPerformanceMetrics()

        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = round((win_count / n) * 100.0, 2)

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.99 if gross_profit > 0 else 0.0)
        total_pnl = sum(pnls)
        expectancy = round(total_pnl / n, 2)

        # R-multiples
        avg_r = 0.0
        if r_multiples and len(r_multiples) > 0:
            avg_r = round(sum(r_multiples) / len(r_multiples), 2)

        # Drawdown calculation
        peak = initial_balance
        current_eq = initial_balance
        max_dd_usd = 0.0
        max_dd_pct = 0.0

        consec_losses = 0
        max_consec_losses = 0

        returns_pct = []

        for p in pnls:
            if p < 0:
                consec_losses += 1
                if consec_losses > max_consec_losses:
                    max_consec_losses = consec_losses
            else:
                consec_losses = 0

            ret = (p / current_eq) if current_eq > 0 else 0.0
            returns_pct.append(ret)

            current_eq += p
            if current_eq > peak:
                peak = current_eq
            dd_usd = peak - current_eq
            dd_pct = (dd_usd / peak) * 100.0 if peak > 0 else 0.0
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd
            if dd_pct > max_dd_pct:
                max_dd_pct = dd_pct

        # Sharpe Ratio (Annualized: sqrt(252))
        sharpe = 0.0
        sortino = 0.0
        calmar = 0.0

        if n >= 3:
            mean_ret = sum(returns_pct) / n
            var_ret = sum((r - mean_ret) ** 2 for r in returns_pct) / (n - 1)
            std_ret = math.sqrt(var_ret) if var_ret > 0 else 0.0

            rf_per_trade = risk_free_rate_annual / 252.0

            if std_ret > 1e-9:
                sharpe = round(((mean_ret - rf_per_trade) / std_ret) * math.sqrt(252), 2)

            # Downside Deviation for Sortino
            downside_sq = [min(0.0, r - rf_per_trade) ** 2 for r in returns_pct]
            downside_var = sum(downside_sq) / n
            downside_std = math.sqrt(downside_var) if downside_var > 0 else 0.0

            if downside_std > 1e-9:
                sortino = round(((mean_ret - rf_per_trade) / downside_std) * math.sqrt(252), 2)

            # Calmar Ratio: (Annualized Return % / Max Drawdown %)
            ann_ret_pct = (mean_ret * 252.0) * 100.0
            if max_dd_pct > 1e-4:
                calmar = round(ann_ret_pct / max_dd_pct, 2)

        return RollingPerformanceMetrics(
            total_trades=n,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate_pct=win_rate,
            profit_factor=profit_factor,
            expectancy_usd=expectancy,
            average_r_multiple=avg_r,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_usd=round(max_dd_usd, 2),
            consecutive_losses_max=max_consec_losses,
            total_pnl_usd=round(total_pnl, 2),
            is_statistically_significant=(n >= 15),
        )

    @staticmethod
    def analyze_slippage_records(
        slippage_pips_list: List[float],
        pip_values_usd: Optional[List[float]] = None
    ) -> SlippagePostMortem:
        n = len(slippage_pips_list)
        if n == 0:
            return SlippagePostMortem()

        adverse = [s for s in slippage_pips_list if s > 0.05]
        favorable = [s for s in slippage_pips_list if s < -0.05]
        zero = [s for s in slippage_pips_list if abs(s) <= 0.05]

        avg_slip = sum(slippage_pips_list) / n
        max_adv = max(slippage_pips_list) if slippage_pips_list else 0.0

        adv_rate = (len(adverse) / n) * 100.0
        fav_rate = (len(favorable) / n) * 100.0
        zero_rate = (len(zero) / n) * 100.0

        # Quality score: penalty for adverse slippage & high average
        score = 100.0 - (adv_rate * 0.5) - (max(0.0, avg_slip) * 15.0)
        score = max(0.0, min(100.0, score))

        cost_usd = 0.0
        if pip_values_usd and len(pip_values_usd) == n:
            cost_usd = sum(s * pv for s, pv in zip(slippage_pips_list, pip_values_usd))

        return SlippagePostMortem(
            total_analyzed_trades=n,
            average_slippage_pips=round(avg_slip, 2),
            max_adverse_slippage_pips=round(max_adv, 2),
            adverse_execution_rate_pct=round(adv_rate, 2),
            favorable_execution_rate_pct=round(fav_rate, 2),
            zero_slippage_rate_pct=round(zero_rate, 2),
            total_slippage_cost_usd=round(cost_usd, 2),
            execution_quality_score=round(score, 1),
        )
