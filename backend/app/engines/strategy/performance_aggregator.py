"""
Strategy Performance Aggregator.
Computes historical performance metrics from closed trades in the journal.
Feeds into Decay Detector for real historical decay sync.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class StrategyPerformance:
    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    profit_factor: float
    expectancy: float
    total_pnl: float
    average_r: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    average_trade_pnl: float
    best_trade_pnl: float
    worst_trade_pnl: float
    sample_size_reliable: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


MIN_RELIABLE_SAMPLE = 10


def compute_strategy_performance(
    strategy_name: str,
    closed_trades: List[Dict[str, Any]]
) -> StrategyPerformance:
    """
    Computes performance metrics from a list of closed trade dicts.
    Each trade dict must have: pnl (float), realized_r (float or None).
    """
    total = len(closed_trades)

    if total == 0:
        return StrategyPerformance(
            strategy_name=strategy_name,
            total_trades=0, wins=0, losses=0, breakeven=0,
            win_rate=0.0, profit_factor=0.0, expectancy=0.0,
            total_pnl=0.0, average_r=0.0, max_drawdown_pct=0.0,
            max_consecutive_losses=0, average_trade_pnl=0.0,
            best_trade_pnl=0.0, worst_trade_pnl=0.0,
            sample_size_reliable=False
        )

    wins = 0
    losses = 0
    breakeven = 0
    gross_profit = 0.0
    gross_loss = 0.0
    r_values = []
    pnl_values = []

    consec_losses = 0
    max_consec = 0
    running_equity = 0.0
    peak_equity = 0.0
    max_dd = 0.0

    for t in closed_trades:
        pnl = float(t.get("pnl", 0.0))
        r_val = t.get("realized_r")
        if r_val is None:
            r_val = 1.0 if pnl > 0 else (-1.0 if pnl < 0 else 0.0)
        r_val = float(r_val)

        pnl_values.append(pnl)
        r_values.append(r_val)
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
        elif pnl < 0:
            losses += 1
            gross_loss += abs(pnl)
            consec_losses += 1
            if consec_losses > max_consec:
                max_consec = consec_losses
        else:
            breakeven += 1
            consec_losses = 0

    win_rate = round((wins / total) * 100.0, 1)
    total_pnl = round(sum(pnl_values), 2)
    avg_r = round(sum(r_values) / total, 2)
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
    expectancy = round(avg_r, 2)
    avg_trade = round(total_pnl / total, 2)
    best = round(max(pnl_values), 2) if pnl_values else 0.0
    worst = round(min(pnl_values), 2) if pnl_values else 0.0
    max_dd_pct = round((max_dd / max(peak_equity, 1.0)) * 100.0, 1) if peak_equity > 0 else 0.0

    return StrategyPerformance(
        strategy_name=strategy_name,
        total_trades=total,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        win_rate=win_rate,
        profit_factor=pf,
        expectancy=expectancy,
        total_pnl=total_pnl,
        average_r=avg_r,
        max_drawdown_pct=max_dd_pct,
        max_consecutive_losses=max_consec,
        average_trade_pnl=avg_trade,
        best_trade_pnl=best,
        worst_trade_pnl=worst,
        sample_size_reliable=total >= MIN_RELIABLE_SAMPLE
    )


def compute_all_strategies_performance(
    all_closed_trades: List[Dict[str, Any]]
) -> Dict[str, StrategyPerformance]:
    """Groups trades by strategy_name and computes per-strategy performance."""
    from collections import defaultdict
    grouped = defaultdict(list)
    for t in all_closed_trades:
        sname = t.get("strategy_name") or "UNKNOWN"
        grouped[sname].append(t)

    results = {}
    for sname, trades in grouped.items():
        results[sname] = compute_strategy_performance(sname, trades)
    return results
