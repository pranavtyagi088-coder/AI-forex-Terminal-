from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import verify_password, create_jwt_token, get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    redirect_to: str

@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    # 1. Check if system is locked
    is_locked = Path("system.lock").exists()
    
    # 2. Look up user
    res = await db.execute(select(User).where(User.username.ilike(req.username.strip())))
    user = res.scalar_one_or_none()
    
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )

    # If system is locked and user is NOT admin -> Return 423 (Locked)
    if is_locked and user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="System locked by Host"
        )

    token = create_jwt_token({
        "sub": str(user.id),
        "username": user.username,
        "role": user.role
    })

    return LoginResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        redirect_to="/admin" if user.role == "admin" else "/dashboard"
    )

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "is_active": user.is_active,
        "created_at": user.created_at
    }
