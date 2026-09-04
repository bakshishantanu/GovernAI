from __future__ import annotations
from uuid import UUID
from sqlalchemy import select, func
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

    async def get_costs_summary(self, org_id: UUID) -> list[dict]:
        # Returns totals grouped by agent, model, and execution
        result = await self.session.execute(
            select(
                CostEvent.agent_id,
                CostEvent.model,
                CostEvent.execution_id,
                func.sum(CostEvent.cost_usd).label("total_cost_usd")
            )
            .where(CostEvent.org_id == org_id)
            .group_by(CostEvent.agent_id, CostEvent.model, CostEvent.execution_id)
        )
        rows = result.all()
        return [
            {
                "agent_id": row.agent_id,
                "model": row.model,
                "execution_id": row.execution_id,
                "total_cost_usd": float(row.total_cost_usd) if row.total_cost_usd else 0.0
            }
            for row in rows
        ]
