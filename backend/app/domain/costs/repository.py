from __future__ import annotations
from datetime import datetime
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

    async def list_costs(
        self,
        org_id: UUID,
        agent_id: UUID | None = None,
        execution_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CostEvent]:
        """Cost events for one org, newest first, optionally narrowed.

        Always scoped by org_id so a caller cannot read another tenant's spend
        by guessing an agent id.
        """
        query = select(CostEvent).where(CostEvent.org_id == org_id)
        if agent_id is not None:
            query = query.where(CostEvent.agent_id == agent_id)
        if execution_id is not None:
            query = query.where(CostEvent.execution_id == execution_id)

        query = query.order_by(CostEvent.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())
