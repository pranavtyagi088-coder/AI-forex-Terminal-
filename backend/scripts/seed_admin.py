import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.core.auth import hash_password
from app.models.user import User

async def seed():
    await init_db()
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.username.ilike("Prime.Tyagi")))
        admin = res.scalar_one_or_none()
        
        if admin:
            admin.password_hash = hash_password("PipHunter@Matrix77")
            admin.role = "admin"
            admin.is_active = True
            await session.commit()
            print("[OK] Super Admin 'Prime.Tyagi' updated successfully!")
        else:
            admin = User(
                username="Prime.Tyagi",
                password_hash=hash_password("PipHunter@Matrix77"),
                role="admin",
                is_active=True
            )
            session.add(admin)
            await session.commit()
            print("[OK] Super Admin 'Prime.Tyagi' seeded successfully!")

if __name__ == "__main__":
    asyncio.run(seed())
