from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.models.trade import Trade
from app.models.strategy import Strategy

@dataclass
class StrategyMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_realized_r: float
    total_realized_r: float
    profit_factor: float
    max_drawdown_pct: float
    consecutive_losses: int
    lifecycle_status: str
    decay_warnings: List[str]

class DecayDetector:
    """
    Module 7: Monitors live rolling trade stats and auto-transitions
    strategy lifecycle state: ACTIVE -> CAUTION -> DEGRADED -> RETIRED
    """

    BASELINE_WIN_RATE = 52.0
    MIN_TRADES_FOR_EVAL = 5

    @classmethod
    def compute_metrics(
        cls,
        trades: List[Trade],
        current_lifecycle: str = "ACTIVE"
    ) -> StrategyMetrics:
        closed_trades = [t for t in trades if t.status == "CLOSED"]
        total = len(closed_trades)

        if total == 0:
            return StrategyMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                avg_realized_r=0.0,
                total_realized_r=0.0,
                profit_factor=0.0,
                max_drawdown_pct=0.0,
                consecutive_losses=0,
                lifecycle_status=current_lifecycle,
                decay_warnings=[]
            )

        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0
        r_list = []

        consec_losses = 0
        max_consec_losses = 0

        running_equity = 0.0
        peak_equity = 0.0
        max_dd = 0.0

        for t in closed_trades:
            pnl = float(t.pnl) if t.pnl is not None else 0.0
            r_val = float(t.realized_r) if t.realized_r is not None else (1.0 if pnl > 0 else -1.0)
            r_list.append(r_val)

            running_equity += pnl
            if running_equity > peak_equity:
                peak_equity = running_equity
            dd = peak_equity - running_equity
            if dd > max_dd:
                max_dd = dd

            if pnl > 0:
                wins += 1
                gross_profit += pnl
                consec_losses = 0
            else:
                losses += 1
                gross_loss += abs(pnl)
                consec_losses += 1
                if consec_losses > max_consec_losses:
                    max_consec_losses = consec_losses

        win_rate = round((wins / total) * 100.0, 1)
        total_r = round(sum(r_list), 2)
        avg_r = round(total_r / total, 2)
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
        max_dd_pct = round((max_dd / 10000.0) * 100.0, 1)

        warnings = []
        new_status = current_lifecycle

        if total >= cls.MIN_TRADES_FOR_EVAL:
            if win_rate < (cls.BASELINE_WIN_RATE - 20.0):
                warnings.append(f"Severe Win Rate Decay: {win_rate}% (Baseline: {cls.BASELINE_WIN_RATE}%)")
                new_status = "DEGRADED"
            elif win_rate < (cls.BASELINE_WIN_RATE - 10.0):
                warnings.append(f"Mild Win Rate Drop: {win_rate}% (Baseline: {cls.BASELINE_WIN_RATE}%)")
                if new_status == "ACTIVE":
                    new_status = "CAUTION"

            if avg_r < -0.2:
                warnings.append(f"Negative Expectancy: Avg R is {avg_r}")
                new_status = "DEGRADED"

            if max_consec_losses >= 5:
                warnings.append(f"Loss Streak Alert: {max_consec_losses} consecutive losses")
                if new_status == "ACTIVE":
                    new_status = "CAUTION"

            if max_dd_pct >= 25.0:
                warnings.append(f"Critical Drawdown: {max_dd_pct}% >= 25.0%")
                new_status = "RETIRED"

        return StrategyMetrics(
            total_trades=total,
            winning_trades=wins,
            losing_trades=losses,
            win_rate=win_rate,
            avg_realized_r=avg_r,
            total_realized_r=total_r,
            profit_factor=profit_factor,
            max_drawdown_pct=max_dd_pct,
            consecutive_losses=max_consec_losses,
            lifecycle_status=new_status,
            decay_warnings=warnings
        )
