from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(tags=["System"])

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "3.0.0",
        "app_version": "3.0.0",
        "database": "connected",
        "environment": getattr(settings, "ENVIRONMENT", "development")
    }

@router.get("/status")
async def system_status():
    return {
        "status": "ok",
        "version": "3.0.0",
        "environment": getattr(settings, "ENVIRONMENT", "development")
    }
