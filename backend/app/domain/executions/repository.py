from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.domain.executions.models import Execution, ExecutionStep

class ExecutionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_execution(self, execution_id: UUID) -> Execution | None:
        result = await self.session.execute(select(Execution).where(Execution.id == execution_id))
        return result.scalar_one_or_none()

    async def create_execution(self, execution: Execution) -> Execution:
        self.session.add(execution)
        return execution
