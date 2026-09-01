from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.agents.models import Agent, AgentPassport

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        result = await self.session.execute(
            select(Agent).options(selectinload(Agent.passport)).where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def list_agents_by_org(self, org_id: UUID, limit: int = 50, offset: int = 0) -> list[Agent]:
        result = await self.session.execute(
            select(Agent)
            .options(selectinload(Agent.passport))
            .where(Agent.org_id == org_id)
            .order_by(Agent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_agents_by_org(self, org_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Agent.id)).where(Agent.org_id == org_id)
        )
        return result.scalar_one()

    async def create_agent(self, agent: Agent) -> Agent:
        self.session.add(agent)
        return agent

    async def create_passport(self, passport: AgentPassport) -> AgentPassport:
        self.session.add(passport)
        return passport
