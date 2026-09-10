from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import hash_password
from app.models.user import User
from app.engines.risk.circuit_breaker import global_circuit_breaker

router = APIRouter(prefix="/api/admin", tags=["admin"])

class CreateUserReq(BaseModel):
    username: str
    password: str
    role: str = "user"

class CircuitBreakerToggleReq(BaseModel):
    enable: bool
    reason: str = "Cockpit Emergency Trigger"

@router.post("/circuit-breaker/toggle")
async def toggle_circuit_breaker(req: CircuitBreakerToggleReq):
    """Toggle system-wide Kill Switch / Circuit Breaker state."""
    if req.enable:
        snap = global_circuit_breaker.force_kill(reason=req.reason)
    else:
        snap = global_circuit_breaker.manual_reset(admin_confirmed=True)
    
    return {
        "status": "success",
        "circuit_breaker_active": snap.state.value == "KILL_SWITCH",
        "circuit_breaker_state": snap.state.value,
        "reason": snap.reason
    }

@router.get("/users")
async def list_users(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User))
    users = res.scalars().all()
    return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active} for u in users]
