import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class MatchScoreLog(Base):
    __tablename__ = "match_score_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    decision = Column(String(20), nullable=False) # TRADE, WAIT, NO_TRADE
    is_safe = Column(Boolean, default=False)
    match_score = Column(Float, nullable=False, default=0.0)
    blocking_reasons = Column(JSON, nullable=True)
    trade_parameters = Column(JSON, nullable=True) # entry, sl, tp, rr, lots
    mtf_validation = Column(JSON, nullable=True)
    market_state_snapshot = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    strategy = relationship("Strategy")
