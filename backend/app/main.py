from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db

# Import all route modules
from app.api.routes import (
    scanner,
    admin,
    analysis,
    auth,
    backtest,
    journal,
    market,
    news,
    performance,
    prop_firm,
    risk,
    strategy,
    system,
    trades,
    upload,
    webhooks
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all API routers
app.include_router(system.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(analysis.router)
app.include_router(backtest.router)
app.include_router(journal.router)
app.include_router(market.router)
app.include_router(news.router)
app.include_router(performance.router)
app.include_router(prop_firm.router)
app.include_router(scanner.router)
app.include_router(risk.router)
app.include_router(strategy.router)
app.include_router(trades.router)
app.include_router(upload.router)
app.include_router(webhooks.router)
