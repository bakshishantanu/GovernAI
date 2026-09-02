from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.policies.models import Policy

class PolicyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_active_policies_for_org(self, org_id: UUID) -> list[Policy]:
        # Fetch only ENABLED policies, and eager-load their ENABLED rules
        stmt = (
            select(Policy)
            .options(selectinload(Policy.rules))
            .where(Policy.org_id == org_id)
            .where(Policy.enabled == True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_policies_for_org(self, org_id: UUID) -> list[Policy]:
        # Keep the old method for backward compatibility if needed elsewhere
        result = await self.session.execute(select(Policy).where(Policy.org_id == org_id))
        return list(result.scalars().all())

    async def create_policy(self, policy: Policy) -> Policy:
        self.session.add(policy)
        return policy
