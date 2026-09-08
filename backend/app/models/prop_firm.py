from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base

class PropFirmProfile(Base):
    __tablename__ = "prop_firm_profiles"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    
    # Core Drawdown Rules
    daily_drawdown_pct = Column(Numeric(5, 2), nullable=False, default=5.0)
    max_drawdown_pct = Column(Numeric(5, 2), nullable=False, default=10.0)
    drawdown_type = Column(String(32), nullable=False, default="STATIC") # STATIC, TRAILING_EQUITY, RELATIVE
    max_loss_basis = Column(String(32), nullable=False, default="BALANCE") # BALANCE, EQUITY, HIGHER_OF_BOTH
    
    # Challenge Targets & Constraints
    profit_target_pct = Column(Numeric(5, 2), nullable=True, default=8.0)
    min_trading_days = Column(Integer, default=0)
    
    # Dynamic Behavioral & Compliance Rules
    allow_weekend_holding = Column(Boolean, nullable=False, default=False)
    allow_news_trading = Column(Boolean, nullable=False, default=False)
    news_blackout_minutes = Column(Integer, nullable=False, default=2)
    max_open_risk_pct = Column(Numeric(5, 2), nullable=False, default=3.0)
    max_lot_per_trade = Column(Numeric(6, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    accounts = relationship("AccountState", back_populates="profile", cascade="all, delete-orphan")

class AccountState(Base):
    __tablename__ = "account_states"

    account_id = Column(String(64), primary_key=True, index=True)
    profile_id = Column(String(64), ForeignKey("prop_firm_profiles.id"), nullable=False)
    starting_balance = Column(Numeric(12, 2), nullable=False, default=100000.0)
    current_balance = Column(Numeric(12, 2), nullable=False, default=100000.0)
    current_equity = Column(Numeric(12, 2), nullable=False, default=100000.0)
    daily_starting_equity = Column(Numeric(12, 2), nullable=False, default=100000.0)
    high_water_mark = Column(Numeric(12, 2), nullable=False, default=100000.0)
    daily_drawdown_limit_usd = Column(Numeric(12, 2), nullable=False, default=5000.0)
    total_drawdown_limit_usd = Column(Numeric(12, 2), nullable=False, default=10000.0)
    current_daily_loss_usd = Column(Numeric(12, 2), nullable=False, default=0.0)
    current_total_loss_usd = Column(Numeric(12, 2), nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="ACTIVE")
    
    # Real Provider / Connection Verification Columns
    data_status = Column(String(32), nullable=False, default="UNAVAILABLE")
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    provider_name = Column(String(64), nullable=True, default="MOCK_PROVIDER")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    profile = relationship("PropFirmProfile", back_populates="accounts")
