from __future__ import annotations
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.costs.models import CostEvent

class CostRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_cost(self, event: CostEvent) -> CostEvent:
        self.session.add(event)
        return event

    async def get_costs_for_agent(self, agent_id: UUID) -> list[CostEvent]:
        result = await self.session.execute(
            select(CostEvent).where(CostEvent.agent_id == agent_id).order_by(CostEvent.timestamp.desc())
        )
        return list(result.scalars().all())
