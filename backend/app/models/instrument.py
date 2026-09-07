"""
Instruments the terminal tracks.
"""

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    pip_size: Mapped[float] = mapped_column(Numeric(12, 8))
    contract_size: Mapped[float] = mapped_column(Numeric(14, 2))
    base_currency: Mapped[str] = mapped_column(String(6))
    quote_currency: Mapped[str] = mapped_column(String(6))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Instrument {self.symbol}>"
