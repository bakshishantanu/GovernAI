from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.agents.models import Agent, AgentPassport, AgentSkill

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _with_relations(self):
        return select(Agent).options(
            selectinload(Agent.passport).selectinload(AgentPassport.permissions)
        )

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        result = await self.session.execute(
            self._with_relations().where(Agent.id == agent_id)
        )
        return result.scalar_one_or_none()

    async def list_agents_by_org(self, org_id: UUID, limit: int = 50, offset: int = 0) -> list[Agent]:
        result = await self.session.execute(
            self._with_relations()
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

    async def add_skill(self, agent_id: UUID, skill_id: str) -> None:
        self.session.add(AgentSkill(agent_id=agent_id, skill_id=skill_id))

    async def flush(self) -> None:
        await self.session.flush()

    async def list_skill_ids(self, agent_id: UUID) -> list[str]:
        result = await self.session.execute(
            select(AgentSkill.skill_id).where(AgentSkill.agent_id == agent_id)
        )
        return list(result.scalars().all())
