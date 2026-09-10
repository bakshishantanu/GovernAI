"""Promote an existing user to the admin role.

Usage:
    uv run python scripts/promote_to_admin.py <user_uuid>

This is the ONLY supported way to grant admin access. There is no
self-service admin registration.
"""
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings
from app.domain.auth.models import Profile

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def promote(user_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Profile).where(Profile.id == user_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            print(f"ERROR: No profile found with id {user_id}")
            sys.exit(1)

        if profile.role == "admin":
            print(f"Profile {user_id} is already an admin.")
            return

        old_role = profile.role
        profile.role = "admin"

        # Attempt to also update Supabase auth.users raw_app_meta_data if possible
        try:
            await session.execute(
                text(
                    "UPDATE auth.users "
                    "SET raw_app_meta_data = COALESCE(raw_app_meta_data, '{}'::jsonb) || '{\"role\": \"admin\"}'::jsonb "
                    "WHERE id = :uid"
                ),
                {"uid": str(user_id)},
            )
        except Exception:
            pass

        await session.commit()
        print(f"SUCCESS: Profile {user_id} promoted from '{old_role}' to 'admin'.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/promote_to_admin.py <user_uuid>")
        sys.exit(1)

    try:
        uid = UUID(sys.argv[1])
    except ValueError:
        print(f"ERROR: '{sys.argv[1]}' is not a valid UUID.")
        sys.exit(1)

    asyncio.run(promote(uid))
