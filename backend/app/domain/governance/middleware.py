from __future__ import annotations
import asyncio
from typing import Any
from uuid import UUID

from app.domain.audit.service import AuditService
from app.domain.policies.engine import PolicyEngine
from app.skills.base import BaseTool

DEFAULT_TOOL_TIMEOUT_SECONDS = 30.0


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
) -> dict:
    """The governance gate every tool call passes through: policy check,
    then (if allowed) timed execution -- with an audit log entry for every
    outcome. Callers still handle the unknown-tool case themselves, since
    there is no BaseTool instance to govern in that case."""
    try:
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
        else:
            result = await asyncio.wait_for(
                tool.execute(**arguments), timeout=timeout_seconds
            )
            await audit_service.log_tool_call(
                org_id, agent_id, execution_id, tool.name, True, "All policies passed"
            )
    except asyncio.TimeoutError:
        result = {
            "error": "timeout",
            "reason": f"tool execution exceeded {timeout_seconds:.0f}s",
        }
    except Exception as exc:
        result = {"error": "tool_failed", "reason": str(exc)}

    return result
