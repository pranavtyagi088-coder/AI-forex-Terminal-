import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    broker = Column(String(20), default="PAPER")
    symbol = Column(String(20), default="EUR/USD")
    timeframe = Column(String(10), nullable=True, default="1h")
    strategy_name = Column(String(64), nullable=True)
    direction = Column(String(10), default="BUY")
    position_size_lots = Column(Float, default=0.1)
    entry_fill = Column(Float, nullable=True)
    exit_fill = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    risk_amount = Column(Float, nullable=True)
    rr_planned = Column(Float, nullable=True)
    pnl = Column(Float, default=0.0)
    realized_r = Column(Float, nullable=True)
    result = Column(String(16), nullable=True, default="OPEN")
    match_score_at_entry = Column(Float, nullable=True)
    slippage = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    status = Column(String(20), default="OPEN")
    market_regime = Column(String(32), nullable=True)
    structure_context = Column(JSON, nullable=True)
    liquidity_context = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    screenshot_ref = Column(String(256), nullable=True)
    market_state_snapshot = Column(JSON, nullable=True)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime, nullable=True)

    strategy = relationship("Strategy")
