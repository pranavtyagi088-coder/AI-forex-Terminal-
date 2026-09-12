from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.engines.events.bus import event_bus
from app.engines.telemetry.ws_manager import ws_manager
from app.engines.telemetry.redis_bus import redis_bus

# ── Router Imports ──
from app.api.routes.admin import router as admin_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.auth import router as auth_router
from app.api.routes.backtest import router as backtest_router
from app.api.routes.journal import router as journal_router
from app.api.routes.market import router as market_router
from app.api.routes.news import router as news_router
from app.api.routes.performance import router as performance_router
from app.api.routes.prop_firm import router as prop_firm_router
from app.api.routes.risk import router as risk_router
from app.api.routes.scanner import router as scanner_router
from app.api.routes.strategy import router as strategy_router
from app.api.routes.system import router as system_router
from app.api.routes.telemetry_routes import router as telemetry_router
from app.api.routes.trades import router as trades_router
from app.api.routes.upload import router as upload_router
from app.api.routes.webhooks import router as webhooks_router
from app.api.routes.ws_telemetry import router as ws_telemetry_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── STARTUP ──
    logger.info("Initializing Institutional AI Forex Terminal...")
    event_bus.register_subscriber(ws_manager.broadcast)
    if settings.REDIS_ENABLED:
        await redis_bus.connect()
    await ws_manager.start_heartbeat()
    yield
    # ── SHUTDOWN ──
    logger.info("Gracefully shutting down Institutional AI Forex Terminal...")
    await ws_manager.stop_heartbeat()
    await ws_manager.disconnect_all()
    if settings.REDIS_ENABLED:
        await redis_bus.close()


app = FastAPI(
    title="Institutional AI Forex Terminal API",
    version="1.0.0",
    description="Deterministic, Evidence-Driven, Risk-First Forex Decision Terminal",
    lifespan=lifespan,
)

# ── CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include All API Routers ──
app.include_router(admin_router)
app.include_router(analysis_router)
app.include_router(auth_router)
app.include_router(backtest_router)
app.include_router(journal_router)
app.include_router(market_router)
app.include_router(news_router)
app.include_router(performance_router)
app.include_router(prop_firm_router)
app.include_router(risk_router)
app.include_router(scanner_router)
app.include_router(strategy_router)
app.include_router(system_router)
app.include_router(telemetry_router)
app.include_router(trades_router)
app.include_router(upload_router)
app.include_router(webhooks_router)
app.include_router(ws_telemetry_router)


@app.get("/")
async def root():
    return {
        "system": "AI Forex Terminal",
        "status": "ONLINE",
        "architecture": "Deterministic Risk-First",
        "rule_enforcement": "Fail-Closed",
    }
