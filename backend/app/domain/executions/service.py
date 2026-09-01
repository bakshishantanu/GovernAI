from __future__ import annotations
from uuid import UUID
from app.domain.executions.models import Execution, ExecutionStep
from app.domain.executions.repository import ExecutionRepository

class ExecutionService:
    def __init__(self, exec_repo: ExecutionRepository):
        self.exec_repo = exec_repo

    async def start_execution(self, agent_id: UUID, org_id: UUID, goal: str) -> Execution:
        execution = Execution(
            agent_id=agent_id,
            org_id=org_id,
            goal=goal,
            status="RUNNING"
        )
        return await self.exec_repo.create_execution(execution)

    async def record_step(self, execution_id: UUID, step_number: int, tool: str, tool_args: dict) -> ExecutionStep:
        execution = await self.exec_repo.get_execution(execution_id)
        if not execution:
            raise ValueError("Execution not found")
            
        step = ExecutionStep(
            execution=execution,
            step_number=step_number,
            tool=tool,
            tool_args=tool_args,
            status="PENDING"
        )
        # Note: In a real app we'd save the step to a repo. For brevity, assuming cascade save.
        return step
