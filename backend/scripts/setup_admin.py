import asyncio
from sqlalchemy import select, text
from app.core.database import AsyncSessionLocal, engine, Base
from app.core.auth import hash_password
from app.models.user import User
from app.main import app

async def setup():
    print("\n--- 1. CHECKING FASTAPI REGISTERED ROUTES ---")
    auth_routes = []
    for route in app.routes:
        if hasattr(route, "path"):
            if "auth" in route.path or "system" in route.path or "admin" in route.path:
                auth_routes.append(f"  [{getattr(route, 'methods', ['GET'])}] {route.path}")
    
    if auth_routes:
        print("\n".join(auth_routes))
    else:
        print("[!] No auth routes found! (Check router inclusion in main.py)")

    print("\n--- 2. INITIALIZING DATABASE TABLES ---")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[OK] All database tables verified & created.")

    print("\n--- 3. SEEDING / VERIFYING SUPER ADMIN USER ---")
    async with AsyncSessionLocal() as session:
        # Check if Prime.Tyagi exists
        res = await session.execute(select(User).where(User.username.ilike("Prime.Tyagi")))
        admin_user = res.scalar_one_or_none()

        if admin_user:
            print(f"[EXISTS] User '{admin_user.username}' already in database! (ID: {admin_user.id}, Role: {admin_user.role})")
            # Update password hash just in case
            admin_user.password_hash = hash_password("PipHunter@Matrix77")
            admin_user.role = "admin"
            admin_user.is_active = True
            await session.commit()
            print("[UPDATED] Password hash refreshed for 'PipHunter@Matrix77'")
        else:
            print("[CREATING] Creating Super Admin 'Prime.Tyagi'...")
            new_admin = User(
                username="Prime.Tyagi",
                password_hash=hash_password("PipHunter@Matrix77"),
                role="admin",
                is_active=True
            )
            session.add(new_admin)
            await session.commit()
            print("[SUCCESS] Super Admin 'Prime.Tyagi' created successfully!")

        # Print all active users
        res_all = await session.execute(select(User))
        all_users = res_all.scalars().all()
        print("\n--- 4. CURRENT ACTIVE USERS IN DATABASE ---")
        for u in all_users:
            print(f"  -> ID: {u.id} | User: {u.username} | Role: {u.role} | Active: {u.is_active}")
        print("-------------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(setup())
