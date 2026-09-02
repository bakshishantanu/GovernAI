from __future__ import annotations
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
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

    async def list_executions_for_org(self, org_id: UUID) -> list[Execution]:
        stmt = (
            select(Execution)
            .options(selectinload(Execution.steps))
            .where(Execution.org_id == org_id)
            .order_by(Execution.started_at.desc())
        )
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
