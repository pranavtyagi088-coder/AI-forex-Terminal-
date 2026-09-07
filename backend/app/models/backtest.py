from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class BacktestRun(Base):
    __tablename__ = "backtest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(10), nullable=False, default="1H")
    initial_balance: Mapped[float] = mapped_column(Float, nullable=False, default=10000.0)
    final_balance: Mapped[float] = mapped_column(Float, nullable=False)
    net_profit: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metrics_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

# Alias to guarantee backward compatibility with app/models/__init__.py
Backtest = BacktestRun
