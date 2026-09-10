import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings

async def check():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT role, count(*) FROM profiles GROUP BY role;"))
        print("Profiles role counts:", res.fetchall())

        res = await conn.execute(text("""
            SELECT conname, pg_get_constraintdef(c.oid)
            FROM pg_constraint c
            JOIN pg_namespace n ON n.oid = c.connamespace
            WHERE conrelid = 'profiles'::regclass;
        """))
        print("Profiles constraints:")
        for row in res.fetchall():
            print(" -", row)

        # Check if handle_new_user trigger exists
        res = await conn.execute(text("""
            SELECT tgname FROM pg_trigger WHERE tgname = 'on_auth_user_created';
        """))
        trigger = res.fetchall()
        print("Auth trigger on_auth_user_created:", trigger)

asyncio.run(check())
