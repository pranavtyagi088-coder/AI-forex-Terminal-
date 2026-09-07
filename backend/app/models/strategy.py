from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import Integer, String, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instrument_id: Mapped[int] = mapped_column(Integer, ForeignKey("instruments.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    evidence_grade: Mapped[str] = mapped_column(String(5), default="B", nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(String(20), default="ACTIVE", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(20), default="1H", nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    instrument = relationship("Instrument", backref="strategies", lazy="joined")
