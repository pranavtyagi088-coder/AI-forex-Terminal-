from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional, Dict, Any


class BacktestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    symbol: str = Field(default="EUR/USD", description="Trading pair")
    timeframe: str = Field(default="1h", description="Candle timeframe")
    strategy: str = Field(default="trend_continuation", description="Strategy ID")
    initial_capital: float = Field(default=10000.0, ge=100.0)
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=5.0)
    slippage_pips: float = Field(default=0.5, ge=0.0, le=10.0)
    commission_per_lot: float = Field(default=7.0, ge=0.0, le=50.0)
    random_seed: Optional[int] = Field(default=None)
    compare_strategies: Optional[List[str]] = Field(default=None)

    # --- Backward Compatibility Fields ---
    initial_balance: Optional[float] = None
    risk_percent: Optional[float] = None
    bars_count: Optional[int] = None
    split_oos: Optional[bool] = None
    strategy_name: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def handle_backward_compatibility(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "initial_balance" in values and "initial_capital" not in values:
                values["initial_capital"] = values["initial_balance"]
            if "risk_percent" in values and "risk_per_trade" not in values:
                values["risk_per_trade"] = values["risk_percent"]
            if "strategy_name" in values and "strategy" not in values:
                values["strategy"] = "trend_continuation"
        return values


class TradeLogItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    entry_bar: int
    exit_bar: int
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    r_multiple: float
    exit_reason: str


class BacktestMetrics(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    expectancy_usd: float
    max_drawdown: float
    max_drawdown_pct: float
    net_profit: float
    net_profit_pct: float
    sharpe_ratio: float
    avg_rr: float
    consecutive_losses: int
    total_bars: int


class BacktestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    symbol: str
    timeframe: str
    strategy: str
    metrics: BacktestMetrics
    trade_log: List[TradeLogItem]
    equity_curve: List[float]
    drawdown_curve: List[float] = Field(default_factory=list)
    is_metrics: Optional[BacktestMetrics] = None
    oos_metrics: Optional[BacktestMetrics] = None
    data_source: str = "synthetic"
    data_quality: Optional[Dict[str, Any]] = None
    slippage_pips_used: float = 0.5
    commission_per_lot_used: float = 7.0

    # --- Backward Compatibility Response Fields ---
    bars_analyzed: Optional[int] = None
    notes: Optional[List[str]] = None
    overall_metrics: Optional[BacktestMetrics] = None
    in_sample_metrics: Optional[BacktestMetrics] = None
    out_of_sample_metrics: Optional[BacktestMetrics] = None


class StrategyComparisonItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy: str
    metrics: BacktestMetrics
    equity_curve: List[float]
    drawdown_curve: List[float]


class StrategyComparisonResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str
    symbol: str
    timeframe: str
    data_source: str
    total_bars: int
    comparisons: List[StrategyComparisonItem]
