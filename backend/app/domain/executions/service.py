from __future__ import annotations
import uuid
from uuid import UUID
from datetime import datetime, timezone
from app.domain.executions.models import Execution, ExecutionStep
from app.domain.executions.repository import ExecutionRepository

class ExecutionService:
    def __init__(self, exec_repo: ExecutionRepository):
        self.exec_repo = exec_repo

    async def create_execution(self, agent_id: UUID, org_id: UUID, goal: str) -> Execution:
        execution = Execution(
            id=uuid.uuid4(),
            agent_id=agent_id,
            org_id=org_id,
            goal=goal,
            status="PENDING",
            started_at=datetime.now(timezone.utc)
        )
        return await self.exec_repo.create_execution(execution)

    async def get_execution(self, execution_id: UUID) -> Execution | None:
        return await self.exec_repo.get_execution(execution_id)

    async def list_executions_for_org(self, org_id: UUID) -> list[Execution]:
        return await self.exec_repo.list_executions_for_org(org_id)

    async def list_executions_for_agent(self, agent_id: UUID) -> list[Execution]:
        return await self.exec_repo.list_executions_for_agent(agent_id)

    async def mark_running(self, execution_id: UUID) -> None:
        await self.exec_repo.complete_execution(execution_id=execution_id, status="RUNNING")

    async def complete(self, execution_id: UUID, result: str | None) -> None:
        await self.exec_repo.complete_execution(execution_id=execution_id, status="COMPLETED", result=result)

    async def fail(self, execution_id: UUID, error: str) -> None:
        await self.exec_repo.complete_execution(execution_id=execution_id, status="FAILED", error=error)

    async def cancel(self, execution_id: UUID, org_id: UUID) -> Execution:
        execution = await self.exec_repo.get_execution(execution_id)
        if not execution or execution.org_id != org_id:
            raise ValueError("Execution not found")
        if execution.status in ("COMPLETED", "FAILED", "CANCELLED", "TERMINATED"):
            raise ValueError(f"Cannot cancel execution in state {execution.status}")
        await self.exec_repo.complete_execution(execution_id=execution_id, status="CANCELLED", error="Manually terminated by user (Kill Switch)")
        return await self.exec_repo.get_execution(execution_id)
