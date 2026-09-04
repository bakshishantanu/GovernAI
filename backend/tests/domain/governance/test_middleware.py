import asyncio
import json
import uuid
from unittest.mock import AsyncMock

from app.domain.governance.middleware import govern_tool
from app.domain.policies.engine import PolicyDecision
from app.skills.base import BaseTool

# Exercises the governance gate on its own -- no LangGraph, no agent loop --
# which is exactly what agent_graph.py's inline policy check couldn't offer.
_ORG_ID = uuid.uuid4()
_AGENT_ID = uuid.uuid4()
_EXECUTION_ID = uuid.uuid4()


class _AllowAllPolicyEngine:
    async def evaluate(self, **kwargs) -> PolicyDecision:
        return PolicyDecision(True, "allowed for test")


class _DenyAllPolicyEngine:
    async def evaluate(self, **kwargs) -> PolicyDecision:
        return PolicyDecision(False, "not permitted")


class _EchoTool(BaseTool):
    name = "echo"
    description = "Echoes text back"
    parameters = {"type": "object", "properties": {"text": {"type": "string"}}}
    required_permission = "echo:use"

    async def execute(self, **kwargs):
        return {"echoed": kwargs["text"]}


class _AlwaysFailTool(BaseTool):
    name = "always_fail"
    description = "Always raises"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        raise RuntimeError("boom")


class _NeverFinishesTool(BaseTool):
    name = "never_finishes"
    description = "Hangs forever"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        await asyncio.sleep(3600)


async def test_allowed_call_executes_the_tool_and_audits_success():
    audit_service = AsyncMock()

    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=audit_service,
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=_EchoTool(),
        arguments={"text": "hi"},
    )

    assert result == {"echoed": "hi"}
    audit_service.log_tool_call.assert_awaited_once_with(
        _ORG_ID, _AGENT_ID, _EXECUTION_ID, "echo", True, "All policies passed"
    )


async def test_denied_call_never_reaches_the_tool_and_audits_denial():
    audit_service = AsyncMock()
    tool = _EchoTool()
    tool.execute = AsyncMock(side_effect=AssertionError("must not be called"))

    result = await govern_tool(
        policy_engine=_DenyAllPolicyEngine(),
        audit_service=audit_service,
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={"text": "hi"},
    )

    assert result == {"error": "denied", "reason": "not permitted"}
    tool.execute.assert_not_called()
    audit_service.log_tool_call.assert_awaited_once_with(
        _ORG_ID, _AGENT_ID, _EXECUTION_ID, "echo", False, "not permitted"
    )


async def test_tool_exception_is_reported_not_raised():
    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=_AlwaysFailTool(),
        arguments={},
    )

    assert result["error"] == "tool_failed"
    assert "boom" in result["reason"]


async def test_hung_tool_is_timed_out_not_left_hanging():
    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=_NeverFinishesTool(),
        arguments={},
        timeout_seconds=0.01,
    )

    assert result["error"] == "timeout"


async def test_required_permission_is_forwarded_to_the_policy_engine():
    policy_engine = _AllowAllPolicyEngine()
    policy_engine.evaluate = AsyncMock(return_value=PolicyDecision(True, "ok"))

    await govern_tool(
        policy_engine=policy_engine,
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=_EchoTool(),
        arguments={"text": "hi"},
    )

    policy_engine.evaluate.assert_awaited_once_with(
        agent_id=_AGENT_ID,
        tool_name="echo",
        tool_args={"text": "hi"},
        required_permission="echo:use",
    )


# --- budget enforcement (FRD-11) and audit ordering -------------------------


class _BudgetGuardStub:
    """Stands in for BudgetGuard without touching the database."""

    def __init__(self, allowed: bool, reason: str = ""):
        self._allowed = allowed
        self._reason = reason
        self.calls = 0

    async def check(self, agent_id, org_id):
        self.calls += 1
        from app.domain.governance.budget import BudgetDecision

        return BudgetDecision(
            allowed=self._allowed, spend_usd=9.99, cap_usd=5.0, reason=self._reason
        )


class _CountingTool(BaseTool):
    name = "counting"
    description = "Records that it ran"
    parameters = {"type": "object", "properties": {}}

    def __init__(self):
        self.runs = 0

    async def execute(self, **kwargs):
        self.runs += 1
        return {"ok": True}


async def test_over_budget_denies_before_the_tool_can_run():
    tool = _CountingTool()
    audit = AsyncMock()
    guard = _BudgetGuardStub(allowed=False, reason="Budget exceeded: $9.99 of $5.00")

    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=audit,
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={},
        budget_guard=guard,
    )

    assert result["error"] == "budget_exceeded"
    assert tool.runs == 0, "an over-budget agent must not reach the tool"
    audit.log_tool_call.assert_awaited_once()
    assert audit.log_tool_call.await_args.args[4] is False  # logged as denied


async def test_budget_is_checked_before_permissions():
    """Being over budget denies the call whatever the permissions say."""
    tool = _CountingTool()
    guard = _BudgetGuardStub(allowed=False, reason="Budget exceeded")

    result = await govern_tool(
        policy_engine=_DenyAllPolicyEngine(),
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={},
        budget_guard=guard,
    )

    assert result["error"] == "budget_exceeded"
    assert guard.calls == 1


async def test_under_budget_runs_the_tool_as_normal():
    tool = _CountingTool()
    guard = _BudgetGuardStub(allowed=True)

    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={},
        budget_guard=guard,
    )

    assert result == {"ok": True}
    assert tool.runs == 1


async def test_no_guard_means_no_budget_check():
    """Omitting the guard leaves existing behaviour untouched."""
    tool = _CountingTool()

    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=AsyncMock(),
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={},
    )

    assert result == {"ok": True}


async def test_a_failed_audit_write_does_not_fake_a_tool_failure():
    """The tool already ran and may have changed the world. Telling the model
    it failed would make it retry and duplicate a real action."""
    tool = _CountingTool()
    audit = AsyncMock()
    audit.log_tool_call.side_effect = RuntimeError("audit table unreachable")

    result = await govern_tool(
        policy_engine=_AllowAllPolicyEngine(),
        audit_service=audit,
        org_id=_ORG_ID,
        agent_id=_AGENT_ID,
        execution_id=_EXECUTION_ID,
        tool=tool,
        arguments={},
    )

    assert result == {"ok": True}, "the real result must survive a logging failure"
    assert tool.runs == 1, "and the tool must not be run twice"
