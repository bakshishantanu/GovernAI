"""Runs an agent after the HTTP response has already been sent.

`POST /executions/` used to `await run_agent(...)` inline, so the request did
not return until the whole run had finished. By the time the caller had an
execution id to stream, there was nothing left to watch — which made the live
run view, and therefore the "watch a tool call get blocked" demo, impossible.

The run now happens here instead, and the endpoint returns immediately.

The important detail is the database session. The request's session is closed by
its dependency as soon as the response is sent, so anything running afterwards
must open its own — using a closed session raises, and sharing one across a
request boundary is worse. Every service below is therefore rebuilt on a fresh
session that this module owns and closes.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.config import settings
from app.domain.agents.kill_switch import KillSwitchService
from app.domain.agents.repository import AgentRepository
from app.domain.audit.repository import AuditRepository
from app.domain.audit.service import AuditService
from app.domain.costs.repository import CostRepository
from app.domain.costs.service import CostService
from app.domain.executions.repository import ExecutionRepository
from app.domain.executions.service import ExecutionService
from app.domain.governance.budget import BudgetGuard
from app.domain.permissions.repository import PermissionRepository
from app.domain.policies.engine import PolicyEngine
from app.domain.policies.repository import PolicyRepository
from app.domain.skills.registry import SkillRegistry
from app.domain.skills.repository import SkillRepository
from app.domain.ticket_drafts.repository import TicketDraftRepository
from app.domain.ticket_drafts.service import TicketDraftService
from app.domain.ticket_drafts.store import ExecutionScopedDraftStore
from app.infrastructure.database import async_session_factory
from app.infrastructure.event_bus import event_bus
from app.runtime.agent_graph import run_agent
from app.runtime.agent_loader import load_agent_tools
from app.runtime.rag.embeddings import GeminiEmbeddingProvider

logger = logging.getLogger(__name__)


async def run_execution(
    *,
    execution_id: UUID,
    agent_id: UUID,
    org_id: UUID,
    goal: str,
    system_prompt: str | None,
    max_steps: int,
    llm_service,
) -> None:
    """Execute one agent run to completion, then record how it ended.

    Never raises. This runs with nobody waiting on it, so an escaping exception
    would be swallowed by the event loop and leave the execution stuck at
    RUNNING forever. Anything unexpected is recorded as a failed run instead.

    `llm_service` is passed in because it holds no database state — it is the
    one dependency worth reusing rather than rebuilding.
    """
    try:
        async with async_session_factory() as session:
            exec_service = ExecutionService(exec_repo=ExecutionRepository(session))
            agent_repo = AgentRepository(session)
            # Named rather than inline: the policy engine's RATE_LIMIT rule
            # counts recent tool calls from this same repository.
            audit_repo = AuditRepository(session)
            audit_service = AuditService(audit_repo=audit_repo, event_bus=event_bus)
            cost_repo = CostRepository(session)

            kill_switch = KillSwitchService(
                session=session,
                agent_repo=agent_repo,
                audit_service=audit_service,
                event_bus=event_bus,
            )

            async def suspend_on_breach(a_id: UUID, o_id: UUID, reason: str) -> None:
                await kill_switch.suspend_agent(
                    agent_id=a_id, actor_id=a_id, org_id=o_id, reason=reason
                )
                await session.commit()

            embedding_provider = (
                GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)
                if settings.GEMINI_API_KEY
                else None
            )

            # Replies the agent composes land here for a human to review.
            # Bound to this run so the drafting tool, which only ever sees the
            # model's own arguments, still records who produced the draft.
            draft_store = ExecutionScopedDraftStore(
                TicketDraftService(repo=TicketDraftRepository(session)),
                org_id=org_id,
                agent_id=agent_id,
                execution_id=execution_id,
            )

            tools = await load_agent_tools(
                agent_id=agent_id,
                agent_repo=agent_repo,
                skill_registry=SkillRegistry(
                    skill_repo=SkillRepository(session),
                    session=session,
                    embedding_provider=embedding_provider,
                    draft_store=draft_store,
                ),
            )

            await exec_service.mark_running(execution_id)
            await session.commit()

            try:
                result = await run_agent(
                    llm_service=llm_service,
                    tools=tools,
                    agent_id=agent_id,
                    org_id=org_id,
                    execution_id=execution_id,
                    policy_engine=PolicyEngine(
                        agent_repo=agent_repo,
                        perm_repo=PermissionRepository(session),
                        policy_repo=PolicyRepository(session),
                        audit_repo=audit_repo,
                    ),
                    audit_service=audit_service,
                    cost_service=CostService(cost_repo=cost_repo, event_bus=event_bus),
                    goal=goal,
                    system_prompt=system_prompt,
                    max_steps=max_steps,
                    budget_guard=BudgetGuard(spend_reader=cost_repo, on_breach=suspend_on_breach),
                )
            except Exception as exc:
                # The run itself failed partway through (e.g. every LLM
                # provider erroring out) -- but real governed work already
                # happened first: tool calls executed, policy decisions were
                # made, LLM calls were billed. Committing THIS session (not
                # falling through to the bare `except` below, which uses a
                # fresh session that knows nothing about any of that) is what
                # keeps that audit trail and cost/budget accounting instead
                # of silently discarding it just because the run didn't
                # finish cleanly. Losing this was worse than losing the final
                # answer: a failed run's real spend never counted against the
                # agent's budget cap at all, and its tool calls vanished from
                # the audit log even though they really happened.
                logger.exception("Background execution %s failed mid-run", execution_id)
                await exec_service.fail(execution_id, error=str(exc))
                await session.commit()
                return

            stopped_reason = result.get("stopped_reason")
            if stopped_reason == "max_steps_reached":
                await exec_service.fail(
                    execution_id,
                    error="Execution stopped: Maximum reasoning steps reached.",
                )
            elif stopped_reason in ("budget_exceeded", "unpriced_model"):
                # agent_node put the exact denial reason (from BudgetGuard) in
                # the last message's content rather than final_answer, since
                # final_answer is reserved for a real answer the agent
                # produced. Falling back to a generic string only protects
                # against a shape change upstream, not an expected case.
                messages = result.get("messages") or []
                reason = (messages[-1].get("content") if messages else None) or (
                    "Execution stopped by governance: cost could not be verified against budget."
                )
                await exec_service.terminate(execution_id, reason=reason)
            else:
                await exec_service.complete(
                    execution_id,
                    result=result.get("final_answer") or "Execution completed.",
                )
            await session.commit()

    except Exception as exc:
        # Reached only for failures *outside* run_agent's own try/except
        # above: the session failing to open, or agent/skill loading failing
        # before the run even started -- nothing governed happened yet, so
        # there is nothing to preserve, and this session may itself be the
        # problem. Nothing is awaiting this, so an escaping exception would
        # be swallowed by the event loop and the run would sit at RUNNING
        # forever, which also means its SSE stream never closes.
        logger.exception("Background execution %s failed before/outside the run", execution_id)
        await _mark_failed(execution_id, str(exc))


async def _mark_failed(execution_id: UUID, error: str) -> None:
    """Record a failure using a session of its own.

    Separate because the failure may have been the session itself; reusing a
    session that is mid-rollback would lose the record of what went wrong.
    """
    try:
        async with async_session_factory() as session:
            service = ExecutionService(exec_repo=ExecutionRepository(session))
            await service.fail(execution_id, error=error)
            await session.commit()
    except Exception:
        logger.exception(
            "Could not record the failure of execution %s; it will stay RUNNING",
            execution_id,
        )
