from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.auth import require_admin, hash_password
from app.models.user import User

router = APIRouter(prefix="/api/admin", tags=["admin"])

class CreateUserReq(BaseModel):
    username: str
    password: str
    role: str = "user"

@router.get("/users")
async def list_users(admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User))
    users = res.scalars().all()
    return [{"id": u.id, "username": u.username, "role": u.role, "is_active": u.is_active} for u in users]

@router.post("/users/create")
async def create_user(req: CreateUserReq, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.username.ilike(req.username.strip())))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    new_user = User(
        username=req.username.strip(),
        password_hash=hash_password(req.password),
        role=req.role
    )
    db.add(new_user)
    await db.commit()
    return {"message": f"User {new_user.username} created successfully"}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}
