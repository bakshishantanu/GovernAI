from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.auth.models import Organization, Profile

class AuthRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_organization(self, org_id: UUID) -> Organization | None:
        result = await self.session.execute(select(Organization).where(Organization.id == org_id))
        return result.scalar_one_or_none()
        
    async def get_profile(self, profile_id: UUID) -> Profile | None:
        result = await self.session.execute(select(Profile).where(Profile.id == profile_id))
        return result.scalar_one_or_none()
