from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.policies.models import Policy, PolicyRule

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
        stmt = (
            select(Policy)
            .options(selectinload(Policy.rules))
            .where(Policy.org_id == org_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_policy(self, policy: Policy) -> Policy:
        self.session.add(policy)
        await self.session.flush()
        return policy

    async def get_policy(self, policy_id: UUID, org_id: UUID) -> Policy | None:
        """One policy with its rules, scoped so another org's id returns nothing."""
        result = await self.session.execute(
            select(Policy)
            .where(Policy.id == policy_id, Policy.org_id == org_id)
            .options(selectinload(Policy.rules))
        )
        return result.scalar_one_or_none()

    async def get_rule(self, rule_id: UUID, org_id: UUID) -> PolicyRule | None:
        """One rule, reached through its policy so org scoping still applies."""
        result = await self.session.execute(
            select(PolicyRule)
            .join(Policy, PolicyRule.policy_id == Policy.id)
            .where(PolicyRule.id == rule_id, Policy.org_id == org_id)
        )
        return result.scalar_one_or_none()

    async def delete_policy(self, policy: Policy) -> None:
        await self.session.delete(policy)
