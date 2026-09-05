from __future__ import annotations
from uuid import UUID
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
from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage
from app.runtime.rag.embeddings import EmbeddingProvider, GeminiEmbeddingProvider
from app.domain.agents.kill_switch import KillSwitchService
from app.domain.governance.budget import BudgetGuard
from app.infrastructure.event_bus import event_bus


class MockFallbackProvider(LLMProvider):
    """Stands in when no provider key is configured, so the console can be run
    and demonstrated locally without a Groq or Gemini account.

    `provider` and `usage` are required on `LLMResponse` and were both missing,
    so every mock call raised TypeError, the service exhausted its retries, and
    *every* run failed with "All LLM providers failed" — i.e. an agent could
    not be run at all without API keys. Zero usage is honest here: no tokens
    were bought, so the cost service records nothing.
    """

    name = "mock"

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        last_msg = messages[-1]["content"] if messages else ""
        return LLMResponse(
            content=f"Execution simulated successfully for prompt: '{last_msg}'",
            model="mock-simulator",
            provider=self.name,
            usage=TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0),
            tool_calls=[],
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
    agent_repo = AgentRepository(db)
    perm_repo = PermissionRepository(db)
    policy_repo = PolicyRepository(db)
    return PolicyEngine(agent_repo=agent_repo, perm_repo=perm_repo, policy_repo=policy_repo)


async def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    repo = AuditRepository(db)
    return AuditService(audit_repo=repo, event_bus=event_bus)


async def get_cost_service(db: AsyncSession = Depends(get_db)) -> CostService:
    repo = CostRepository(db)
    return CostService(cost_repo=repo, event_bus=event_bus)


def get_embedding_provider() -> EmbeddingProvider | None:
    if not settings.GEMINI_API_KEY:
        return None
    return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)


async def get_skill_registry(
    db: AsyncSession = Depends(get_db),
    embedding_provider: EmbeddingProvider | None = Depends(get_embedding_provider),
) -> SkillRegistry:
    repo = SkillRepository(db)
    return SkillRegistry(skill_repo=repo, session=db, embedding_provider=embedding_provider)


async def get_kill_switch_service(db: AsyncSession = Depends(get_db)) -> KillSwitchService:
    """Suspend / reactivate an agent, with the audit entry written alongside."""
    return KillSwitchService(
        session=db,
        agent_repo=AgentRepository(db),
        audit_service=AuditService(audit_repo=AuditRepository(db), event_bus=event_bus),
        event_bus=event_bus,
    )
async def get_budget_guard(db: AsyncSession = Depends(get_db)) -> BudgetGuard:
    """The live spend check the governance gate runs before every tool call.

    On a breach the agent is suspended, not merely blocked — FRD-11 requires
    the platform to stop an over-budget agent by itself. The suspension is
    injected as a callback so the guard stays independent of the kill switch.
    """
    cost_repo = CostRepository(db)
    audit_service = AuditService(audit_repo=AuditRepository(db), event_bus=event_bus)
    kill_switch = KillSwitchService(
        session=db,
        agent_repo=AgentRepository(db),
        audit_service=audit_service,
        event_bus=event_bus,
    )

    async def suspend_on_breach(agent_id: UUID, org_id: UUID, reason: str) -> None:
        # The agent itself is the actor here: nobody pressed a button.
        await kill_switch.suspend_agent(
            agent_id=agent_id, actor_id=agent_id, org_id=org_id, reason=reason
        )
        await db.commit()

    return BudgetGuard(spend_reader=cost_repo, on_breach=suspend_on_breach)
