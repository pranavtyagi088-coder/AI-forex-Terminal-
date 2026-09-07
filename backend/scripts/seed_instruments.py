"""
Seed script to populate standard instruments in the database.
"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, init_db
from app.models.instrument import Instrument

# Core 10 instruments as specified in the blueprint & strategy libraries
CORE_INSTRUMENTS = [
    {"symbol": "EUR/USD", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "EUR", "quote_currency": "USD"},
    {"symbol": "GBP/USD", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "GBP", "quote_currency": "USD"},
    {"symbol": "AUD/USD", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "AUD", "quote_currency": "USD"},
    {"symbol": "NZD/USD", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "NZD", "quote_currency": "USD"},
    {"symbol": "USD/JPY", "pip_size": 0.01, "contract_size": 100000.0, "base_currency": "USD", "quote_currency": "JPY"},
    {"symbol": "USD/CHF", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "USD", "quote_currency": "CHF"},
    {"symbol": "USD/CAD", "pip_size": 0.0001, "contract_size": 100000.0, "base_currency": "USD", "quote_currency": "CAD"},
    {"symbol": "XAU/USD", "pip_size": 0.01, "contract_size": 100.0, "base_currency": "XAU", "quote_currency": "USD"},
    {"symbol": "BTC/USD", "pip_size": 1.0, "contract_size": 1.0, "base_currency": "BTC", "quote_currency": "USD"},
    {"symbol": "GBP/JPY", "pip_size": 0.01, "contract_size": 100000.0, "base_currency": "GBP", "quote_currency": "JPY"},
]

async def seed():
    print("Initializing database tables...")
    await init_db()
    
    async with AsyncSessionLocal() as session:
        print("Checking existing instruments...")
        for data in CORE_INSTRUMENTS:
            result = await session.execute(
                select(Instrument).where(Instrument.symbol == data["symbol"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                instrument = Instrument(
                    symbol=data["symbol"],
                    pip_size=data["pip_size"],
                    contract_size=data["contract_size"],
                    base_currency=data["base_currency"],
                    quote_currency=data["quote_currency"],
                    active=True
                )
                session.add(instrument)
                print(f"Adding {data['symbol']}...")
            else:
                print(f"{data['symbol']} already exists, skipping.")
                
        await session.commit()
    print("Seeding completed successfully!")

if __name__ == "__main__":
    # Windows system par ProactorEventLoop issue se bachne ke liye standard run
    asyncio.run(seed())
