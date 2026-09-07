from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select
from app.core.config import settings

class Base(DeclarativeBase):
    pass

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    import app.models.user
    import app.models.instrument
    import app.models.ohlcv
    import app.models.strategy
    import app.models.analysis
    import app.models.trade
    import app.models.risk_state
    import app.models.alert
    import app.models.backtest
    import app.models.match_log
    import app.models.decay_flag
    import app.models.prop_firm

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        from app.models.instrument import Instrument
        inst_res = await session.execute(select(Instrument))
        if not inst_res.scalars().first():
            instruments = [
                Instrument(symbol="EUR/USD", pip_size=0.0001, contract_size=100000.0, base_currency="EUR", quote_currency="USD", active=True),
                Instrument(symbol="USD/JPY", pip_size=0.01, contract_size=100000.0, base_currency="USD", quote_currency="JPY", active=True),
                Instrument(symbol="GBP/USD", pip_size=0.0001, contract_size=100000.0, base_currency="GBP", quote_currency="USD", active=True),
                Instrument(symbol="GBP/JPY", pip_size=0.01, contract_size=100000.0, base_currency="GBP", quote_currency="JPY", active=True),
                Instrument(symbol="EURUSD", pip_size=0.0001, contract_size=100000.0, base_currency="EUR", quote_currency="USD", active=True),
            ]
            session.add_all(instruments)
            await session.commit()

        from app.models.strategy import Strategy
        strat_res = await session.execute(select(Strategy))
        if not strat_res.scalars().first():
            eur = await session.execute(select(Instrument).where(Instrument.symbol == "EUR/USD"))
            eur_inst = eur.scalar_one()
            strategies = [
                Strategy(instrument_id=eur_inst.id, name="Trend Following M15", evidence_grade="A", lifecycle_status="HEALTHY"),
                Strategy(instrument_id=eur_inst.id, name="Liquidity Sweep H1", evidence_grade="B", lifecycle_status="HEALTHY"),
            ]
            session.add_all(strategies)
            await session.commit()
