from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, Text, JSON
from app.core.database import Base

class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(String(64), primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True, default="EURUSD")
    timeframe = Column(String(10), nullable=False, default="15")
    direction = Column(String(16), nullable=False, default="BUY")
    confidence = Column(Float, nullable=False, default=0.0)
    bias = Column(String(32), nullable=False, default="NEUTRAL")
    signal = Column(String(16), nullable=True, default="BUY")
    score_total = Column(Float, nullable=True, default=75.0)
    risk_reward_ratio = Column(Float, nullable=True, default=2.0)
    rr_ratio = Column(Float, nullable=True, default=2.0)
    chart_images = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    raw_response = Column(Text, nullable=True)
    data_status = Column(String(32), nullable=True, default="FRESH")
    no_trade_reasons = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
