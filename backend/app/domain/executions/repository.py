from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.executions.models import Execution, ExecutionStep


class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_execution(self, execution_id: UUID) -> Execution | None:
        stmt = (
            select(Execution)
            .options(selectinload(Execution.steps))
            .where(Execution.id == execution_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_executions_for_org(
        self,
        org_id: UUID,
        builder_id: UUID | None = None,
        assigned_user_id: UUID | None = None,
    ) -> list[Execution]:
        from app.domain.agents.models import Agent

        stmt = (
            select(Execution)
            .options(selectinload(Execution.steps))
            .join(Agent, Execution.agent_id == Agent.id)
            .where(Execution.org_id == org_id)
        )
        # OR, not AND-via-two-elifs: a merged user can be the owner of some
        # agents and only the assignee of others, and must see executions for
        # both. Callers pass their own id as both parameters, landing here.
        if builder_id and assigned_user_id:
            stmt = stmt.where(
                or_(Agent.owner_id == builder_id, Agent.assigned_user_id == assigned_user_id)
            )
        elif builder_id:
            stmt = stmt.where(Agent.owner_id == builder_id)
        elif assigned_user_id:
            stmt = stmt.where(Agent.assigned_user_id == assigned_user_id)

        stmt = stmt.order_by(Execution.started_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_executions_for_agent(self, agent_id: UUID) -> list[Execution]:
        stmt = (
            select(Execution)
            .options(selectinload(Execution.steps))
            .where(Execution.agent_id == agent_id)
            .order_by(Execution.started_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_execution(self, execution: Execution) -> Execution:
        self.session.add(execution)
        await self.session.flush()
        return execution

    async def complete_execution(
        self, execution_id: UUID, status: str, result: str | None = None, error: str | None = None
    ) -> None:
        stmt = (
            update(Execution)
            .where(Execution.id == execution_id)
            .values(
                status=status,
                result=result,
                error=error,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def record_step(self, step: ExecutionStep) -> ExecutionStep:
        self.session.add(step)
        await self.session.flush()
        return step
