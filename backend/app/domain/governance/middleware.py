from __future__ import annotations
import asyncio
import logging
from typing import Any
from uuid import UUID

from app.domain.audit.service import AuditService
from app.domain.governance.budget import BudgetGuard
from app.domain.policies.engine import PolicyEngine
from app.skills.base import BaseTool

DEFAULT_TOOL_TIMEOUT_SECONDS = 30.0

logger = logging.getLogger(__name__)


async def govern_tool(
    *,
    policy_engine: PolicyEngine,
    audit_service: AuditService,
    org_id: UUID,
    agent_id: UUID,
    execution_id: UUID,
    tool: BaseTool,
    arguments: dict[str, Any],
    timeout_seconds: float = DEFAULT_TOOL_TIMEOUT_SECONDS,
    budget_guard: BudgetGuard | None = None,
) -> dict:
    """The governance gate every tool call passes through: budget check, policy
    check, then (if allowed) timed execution -- with an audit log entry for
    every outcome. Callers still handle the unknown-tool case themselves, since
    there is no BaseTool instance to govern in that case."""
    try:
        # Budget first: an agent over its cap is denied whatever its permissions
        # say, and FRD-11 requires it to be suspended rather than merely blocked.
        if budget_guard is not None:
            budget = await budget_guard.check(agent_id, org_id)
            if not budget.allowed:
                await audit_service.log_tool_call(
                    org_id, agent_id, execution_id, tool.name, False, budget.reason
                )
                return {"error": "budget_exceeded", "reason": budget.reason}

        decision = await policy_engine.evaluate(
            agent_id=agent_id,
            tool_name=tool.name,
            tool_args=arguments,
            required_permission=getattr(tool, "required_permission", "")
        )

        if not decision.allowed:
            result = {"error": "denied", "reason": decision.reason}
            await audit_service.log_tool_call(
                org_id, agent_id, execution_id, tool.name, False, decision.reason
            )
            return result

        result = await asyncio.wait_for(
            tool.execute(**arguments), timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        return {
            "error": "timeout",
            "reason": f"tool execution exceeded {timeout_seconds:.0f}s",
        }
    except Exception as exc:
        return {"error": "tool_failed", "reason": str(exc)}

    # The tool has already run and may have changed the outside world. A failed
    # audit write must not be reported to the model as a failed tool: it would
    # retry and duplicate a real action. Return the true result and make the
    # logging failure loud instead.
    try:
        await audit_service.log_tool_call(
            org_id, agent_id, execution_id, tool.name, True, "All policies passed"
        )
    except Exception:
        logger.exception(
            "AUDIT WRITE FAILED after a successful tool call — "
            "agent=%s execution=%s tool=%s. The action happened but is unlogged.",
            agent_id, execution_id, tool.name,
        )

    return result
