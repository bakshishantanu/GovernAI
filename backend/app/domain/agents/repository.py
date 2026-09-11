from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.agents.models import Agent, AgentPassport, AgentSkill
from app.domain.auth.models import Profile


class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _with_relations(self):
        return select(Agent).options(
            selectinload(Agent.passport).selectinload(AgentPassport.permissions)
        )

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        result = await self.session.execute(self._with_relations().where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def list_agents_by_org(
        self,
        org_id: UUID,
        limit: int = 50,
        offset: int = 0,
        owner_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> list[Agent]:
        query = self._with_relations().where(Agent.org_id == org_id)
        if owner_id and assigned_user_id:
            query = query.where(
                or_(Agent.owner_id == owner_id, Agent.assigned_user_id == assigned_user_id)
            )
        elif owner_id:
            query = query.where(Agent.owner_id == owner_id)
        elif assigned_user_id:
            query = query.where(Agent.assigned_user_id == assigned_user_id)

        result = await self.session.execute(
            query.order_by(Agent.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def count_agents_by_org(
        self,
        org_id: UUID,
        owner_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> int:
        query = select(func.count(Agent.id)).where(Agent.org_id == org_id)
        if owner_id and assigned_user_id:
            query = query.where(
                or_(Agent.owner_id == owner_id, Agent.assigned_user_id == assigned_user_id)
            )
        elif owner_id:
            query = query.where(Agent.owner_id == owner_id)
        elif assigned_user_id:
            query = query.where(Agent.assigned_user_id == assigned_user_id)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def owner_is_in_org(self, owner_id: UUID, org_id: UUID) -> bool:
        """Whether this agent's owner is a real profile in this agent's org.

        Compliance rule 1 is "the agent has an owner". Read only as "owner_id is
        set" it can never fail through the API, because the column is NOT NULL
        and the value comes from the caller's own token. Read as "the owner is a
        person this organisation knows" it can: a profile can be deleted, and an
        owner_id copied from elsewhere points outside the org. That is the
        version worth checking.
        """
        result = await self.session.execute(
            select(Profile.id).where(Profile.id == owner_id, Profile.org_id == org_id)
        )
        return result.scalar_one_or_none() is not None

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

    async def list_active_agents_with_skill(self, skill_id: str) -> list[Agent]:
        """Every ACTIVE agent, across every org, with the given skill bound.

        Used by event-driven triggers (e.g. the Jira webhook) that have no
        org context of their own to scope by -- unlike a normal HTTP request,
        which always knows its org from the caller's JWT.
        """
        result = await self.session.execute(
            self._with_relations()
            .join(AgentSkill, AgentSkill.agent_id == Agent.id)
            .join(AgentPassport, AgentPassport.agent_id == Agent.id)
            .where(AgentSkill.skill_id == skill_id, AgentPassport.lifecycle_state == "ACTIVE")
        )
        return list(result.scalars().unique().all())
