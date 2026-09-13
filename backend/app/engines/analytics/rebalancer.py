from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel
from app.engines.analytics.metrics import RollingPerformanceMetrics


class StrategyWeightAllocation(BaseModel):
    strategy_id: str
    strategy_name: str
    current_status: str
    recommended_status: str
    risk_multiplier: float  # 0.0 to 1.0 multiplier for standard lot size
    rebalance_reason: str
    is_throttled: bool


class AdaptiveWeightRebalancer:
    """Dynamically adjusts risk allocation weights based on closed-loop trade metrics."""

    @classmethod
    def evaluate_strategy_weight(
        cls,
        strategy_id: str,
        strategy_name: str,
        metrics: RollingPerformanceMetrics,
        current_status: str = "ACTIVE",
    ) -> StrategyWeightAllocation:
        # 1. Cold start: Insufficient data -> Standard neutral risk
        if metrics.total_trades < 5:
            return StrategyWeightAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                current_status=current_status,
                recommended_status=current_status,
                risk_multiplier=1.0,
                rebalance_reason="Sample size < 5 (Observation phase)",
                is_throttled=False,
            )

        # 2. Severe Drawdown / Ruin Prevention -> RETIRED (0.0x)
        if metrics.max_drawdown_pct >= 5.0 or metrics.consecutive_losses_max >= 6:
            return StrategyWeightAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                current_status=current_status,
                recommended_status="RETIRED",
                risk_multiplier=0.0,
                rebalance_reason=f"Severe degradation: Max DD {metrics.max_drawdown_pct}% >= 5.0% or 6+ consecutive losses",
                is_throttled=True,
            )

        # 3. Degraded Performance -> DEGRADED (0.25x)
        if metrics.sortino_ratio < 0.5 or metrics.profit_factor < 0.8 or metrics.consecutive_losses_max >= 4:
            return StrategyWeightAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                current_status=current_status,
                recommended_status="DEGRADED",
                risk_multiplier=0.25,
                rebalance_reason=f"Degraded: Sortino {metrics.sortino_ratio} < 0.5 or PF {metrics.profit_factor} < 0.8",
                is_throttled=True,
            )

        # 4. Caution Threshold -> CAUTION (0.50x)
        if metrics.sortino_ratio < 1.0 or metrics.max_drawdown_pct >= 3.0 or metrics.win_rate_pct < 45.0:
            return StrategyWeightAllocation(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                current_status=current_status,
                recommended_status="CAUTION",
                risk_multiplier=0.5,
                rebalance_reason=f"Caution: Sub-optimal Sortino {metrics.sortino_ratio} or DD {metrics.max_drawdown_pct}%",
                is_throttled=True,
            )

        # 5. Peak Health -> ACTIVE (1.0x)
        return StrategyWeightAllocation(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            current_status=current_status,
            recommended_status="ACTIVE",
            risk_multiplier=1.0,
            rebalance_reason="Optimal risk-adjusted performance",
            is_throttled=False,
        )
