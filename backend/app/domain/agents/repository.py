from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.agents.models import Agent, AgentPassport

class AgentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_agent(self, agent_id: UUID) -> Agent | None:
        result = await self.session.execute(select(Agent).where(Agent.id == agent_id))
        return result.scalar_one_or_none()

    async def create_agent(self, agent: Agent) -> Agent:
        self.session.add(agent)
        return agent

    async def create_passport(self, passport: AgentPassport) -> AgentPassport:
        self.session.add(passport)
        return passport
