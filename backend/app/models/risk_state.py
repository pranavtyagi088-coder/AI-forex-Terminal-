"""
Account-level risk state.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.database import Base


class RiskState(Base):
    __tablename__ = "risk_state"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_label: Mapped[str] = mapped_column(String(50))
    balance: Mapped[float] = mapped_column(Numeric(14, 2))
    daily_loss_limit_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_drawdown_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    max_leverage: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
