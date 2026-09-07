import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class DecayFlag(Base):
    __tablename__ = "decay_flags"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    flag_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)
    baseline_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    strategy = relationship("Strategy")
