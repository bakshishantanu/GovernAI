from __future__ import annotations
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.infrastructure.database import get_db
from app.domain.agents.repository import AgentRepository
from app.domain.agents.service import AgentService
from app.domain.permissions.repository import PermissionRepository
from app.domain.skills.repository import SkillRepository
from app.domain.skills.registry import SkillRegistry
from app.domain.policies.engine import PolicyEngine
from app.domain.policies.repository import PolicyRepository
from app.domain.audit.repository import AuditRepository
from app.domain.audit.service import AuditService
from app.domain.costs.repository import CostRepository
from app.domain.costs.service import CostService
from app.domain.executions.repository import ExecutionRepository
from app.domain.executions.service import ExecutionService
from app.runtime.llm.service import LLMService
from app.runtime.llm.gemini import GeminiProvider
from app.runtime.llm.groq import GroqProvider
from app.runtime.llm.base import LLMProvider, LLMResponse


class MockFallbackProvider(LLMProvider):
    name = "mock"

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        last_msg = messages[-1]["content"] if messages else ""
        return LLMResponse(
            content=f"Execution simulated successfully for prompt: '{last_msg}'",
            tool_calls=[],
            model="mock-simulator",
        )


def get_llm_service() -> LLMService:
    providers: list[LLMProvider] = []
    if settings.GROQ_API_KEY:
        providers.append(GroqProvider(api_key=settings.GROQ_API_KEY, model=settings.LLM_PRIMARY_MODEL))
    if settings.GEMINI_API_KEY:
        providers.append(GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.LLM_FALLBACK_MODEL))
    if not providers:
        providers.append(MockFallbackProvider())
    return LLMService(providers)


async def get_agent_service(db: AsyncSession = Depends(get_db)) -> AgentService:
    agent_repo = AgentRepository(db)
    perm_repo = PermissionRepository(db)
    skill_repo = SkillRepository(db)
    return AgentService(agent_repo=agent_repo, perm_repo=perm_repo, skill_repo=skill_repo)


async def get_execution_service(db: AsyncSession = Depends(get_db)) -> ExecutionService:
    exec_repo = ExecutionRepository(db)
    return ExecutionService(exec_repo=exec_repo)


async def get_policy_engine(db: AsyncSession = Depends(get_db)) -> PolicyEngine:
    return PolicyEngine(session=db)


async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    repo = AuditRepository(db)
    return AuditService(repo=repo)


async def get_cost_service(db: AsyncSession = Depends(get_db)) -> CostService:
    repo = CostRepository(db)
    return CostService(repo=repo)


async def get_skill_registry(db: AsyncSession = Depends(get_db)) -> SkillRegistry:
    repo = SkillRepository(db)
    return SkillRegistry(skill_repo=repo, session=db)
