"""
OHLCV candle storage.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OHLCV(Base):
    __tablename__ = "ohlcv"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id"), primary_key=True)
    timeframe: Mapped[str] = mapped_column(String(4), primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)

    open: Mapped[float] = mapped_column(Numeric(18, 6))
    high: Mapped[float] = mapped_column(Numeric(18, 6))
    low: Mapped[float] = mapped_column(Numeric(18, 6))
    close: Mapped[float] = mapped_column(Numeric(18, 6))
    volume: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    source: Mapped[str] = mapped_column(String(30))
