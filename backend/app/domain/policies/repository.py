from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.policies.models import Policy, PolicyRule

class PolicyRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_policies_for_org(self, org_id: UUID) -> list[Policy]:
        result = await self.session.execute(select(Policy).where(Policy.org_id == org_id))
        return list(result.scalars().all())

    async def create_policy(self, policy: Policy) -> Policy:
        self.session.add(policy)
        return policy
