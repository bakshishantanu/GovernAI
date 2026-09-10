from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
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
            select(CostEvent)
            .where(CostEvent.agent_id == agent_id)
            .order_by(CostEvent.timestamp.desc())
        )
        return list(result.scalars().all())

    async def get_costs_summary(
        self,
        org_id: UUID,
        builder_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> list[dict]:
        from app.domain.agents.models import Agent

        # Returns totals grouped by agent, model, and execution
        query = (
            select(
                CostEvent.agent_id,
                CostEvent.model,
                CostEvent.execution_id,
                func.sum(CostEvent.cost_usd).label("total_cost_usd"),
            )
            .where(CostEvent.org_id == org_id)
        )

        if builder_id or assigned_user_id:
            query = query.outerjoin(Agent, CostEvent.agent_id == Agent.id)
            if builder_id and assigned_user_id:
                query = query.where(
                    or_(Agent.owner_id == builder_id, Agent.assigned_user_id == assigned_user_id)
                )
            elif builder_id:
                query = query.where(Agent.owner_id == builder_id)
            else:
                query = query.where(Agent.assigned_user_id == assigned_user_id)

        result = await self.session.execute(
            query.group_by(CostEvent.agent_id, CostEvent.model, CostEvent.execution_id)
        )
        rows = result.all()
        return [
            {
                "agent_id": row.agent_id,
                "model": row.model,
                "execution_id": row.execution_id,
                "total_cost_usd": float(row.total_cost_usd) if row.total_cost_usd else 0.0,
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
        builder_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> list[CostEvent]:
        """Cost events for one org, newest first, optionally narrowed.

        Always scoped by org_id so a caller cannot read another tenant's spend
        by guessing an agent id.
        """
        from app.domain.agents.models import Agent

        query = select(CostEvent).where(CostEvent.org_id == org_id)
        if agent_id is not None:
            query = query.where(CostEvent.agent_id == agent_id)
        if execution_id is not None:
            query = query.where(CostEvent.execution_id == execution_id)

        if builder_id or assigned_user_id:
            query = query.outerjoin(Agent, CostEvent.agent_id == Agent.id)
            if builder_id and assigned_user_id:
                query = query.where(
                    or_(Agent.owner_id == builder_id, Agent.assigned_user_id == assigned_user_id)
                )
            elif builder_id:
                query = query.where(Agent.owner_id == builder_id)
            else:
                query = query.where(Agent.assigned_user_id == assigned_user_id)

        query = query.order_by(CostEvent.timestamp.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_cost_for_agent(self, agent_id: UUID, since: datetime) -> float:
        """Total USD spent by one agent since `since`.

        Summed in the database rather than in Python: the budget guard calls
        this before every tool call, so it must not load one row per LLM call
        an agent has ever made.
        """
        result = await self.session.execute(
            select(func.coalesce(func.sum(CostEvent.cost_usd), 0.0))
            .where(CostEvent.agent_id == agent_id)
            .where(CostEvent.timestamp >= since)
        )
        return float(result.scalar_one() or 0.0)
