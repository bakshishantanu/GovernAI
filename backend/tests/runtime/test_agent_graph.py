import json
from uuid import uuid4

from app.runtime.agent_graph import run_agent
from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall
from app.runtime.llm.service import LLMService
from app.domain.policies.engine import PolicyDecision
from app.skills.base import BaseTool

# These tests exercise the graph's reasoning-loop mechanics (tool dispatch,
# error handling, max_steps) in isolation from governance -- matching the
# project's stub strategy of an always-ALLOW policy engine for early
# LangGraph testing. Real policy enforcement is covered by the policy
# engine's own tests.
_TEST_AGENT_ID = uuid4()


class _AllowAllPolicyEngine:
    async def evaluate(self, **kwargs) -> PolicyDecision:
        return PolicyDecision(True, "test bypass")


class _DenyAllPolicyEngine:
    async def evaluate(self, **kwargs) -> PolicyDecision:
        return PolicyDecision(False, "not permitted")


class _ScriptedProvider(LLMProvider):
    """Returns pre-built LLMResponses in sequence - full control over what
    the 'LLM' does at each turn, no network calls."""

    name = "scripted"

    def __init__(self, responses: list[LLMResponse]):
        self._responses = list(responses)
        self.call_count = 0

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        response = self._responses[self.call_count]
        self.call_count += 1
        return response


class _InfiniteToolCaller(LLMProvider):
    """Always calls a tool, never produces a final answer - used to prove
    the max_steps guard actually stops the loop."""

    name = "infinite"

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        call_index = sum(1 for m in messages if m["role"] == "assistant")
        return LLMResponse(
            content="",
            model="m",
            provider="infinite",
            usage=TokenUsage(1, 1, 2),
            tool_calls=[ToolCall(id=f"call_{call_index}", name="echo", arguments={"text": "loop"})],
        )


class _EchoTool(BaseTool):
    name = "echo"
    description = "Echoes text back"
    parameters = {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    }

    async def execute(self, **kwargs):
        return {"echoed": kwargs["text"]}


class _AlwaysFailTool(BaseTool):
    name = "always_fail"
    description = "Always raises"
    parameters = {"type": "object", "properties": {}}

    async def execute(self, **kwargs):
        raise RuntimeError("boom")


def _resp(content: str = "", tool_calls: list[ToolCall] | None = None) -> LLMResponse:
    return LLMResponse(
        content=content,
        model="m",
        provider="scripted",
        usage=TokenUsage(1, 1, 2),
        tool_calls=tool_calls or [],
    )


async def test_agent_completes_without_any_tool_call():
    provider = _ScriptedProvider([_resp("the answer is 42")])
    service = LLMService([provider])

    result = await run_agent(
        service, tools=[], agent_id=_TEST_AGENT_ID, policy_engine=_AllowAllPolicyEngine(), goal="what is the answer?"
    )

    assert result["final_answer"] == "the answer is 42"
    assert result["steps"] == 1
    assert result["stopped_reason"] == "completed"


async def test_agent_calls_a_tool_then_produces_final_answer():
    tool_call = ToolCall(id="call_1", name="echo", arguments={"text": "hi"})
    provider = _ScriptedProvider([_resp(tool_calls=[tool_call]), _resp("I echoed: hi")])
    service = LLMService([provider])

    result = await run_agent(
        service, tools=[_EchoTool()], agent_id=_TEST_AGENT_ID, policy_engine=_AllowAllPolicyEngine(), goal="echo hi"
    )

    assert result["final_answer"] == "I echoed: hi"
    assert result["steps"] == 2
    tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == 1
    assert json.loads(tool_messages[0]["content"]) == {"echoed": "hi"}


async def test_multiple_tool_calls_in_one_turn_all_execute():
    tool_calls = [
        ToolCall(id="call_1", name="echo", arguments={"text": "a"}),
        ToolCall(id="call_2", name="echo", arguments={"text": "b"}),
    ]
    provider = _ScriptedProvider([_resp(tool_calls=tool_calls), _resp("done")])
    service = LLMService([provider])

    result = await run_agent(
        service, tools=[_EchoTool()], agent_id=_TEST_AGENT_ID, policy_engine=_AllowAllPolicyEngine(), goal="echo a and b"
    )

    tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
    assert len(tool_messages) == 2
    assert {json.loads(m["content"])["echoed"] for m in tool_messages} == {"a", "b"}


async def test_unknown_tool_call_does_not_crash_the_run():
    tool_call = ToolCall(id="call_1", name="does_not_exist", arguments={})
    provider = _ScriptedProvider([_resp(tool_calls=[tool_call]), _resp("couldn't find that tool")])
    service = LLMService([provider])

    result = await run_agent(
        service, tools=[], agent_id=_TEST_AGENT_ID, policy_engine=_AllowAllPolicyEngine(), goal="do something"
    )

    tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
    payload = json.loads(tool_messages[0]["content"])
    assert payload["error"] == "unknown_tool"
    assert result["final_answer"] == "couldn't find that tool"


async def test_tool_exception_is_caught_and_reported_not_raised():
    tool_call = ToolCall(id="call_1", name="always_fail", arguments={})
    provider = _ScriptedProvider([_resp(tool_calls=[tool_call]), _resp("that failed")])
    service = LLMService([provider])

    result = await run_agent(
        service,
        tools=[_AlwaysFailTool()],
        agent_id=_TEST_AGENT_ID,
        policy_engine=_AllowAllPolicyEngine(),
        goal="fail please",
    )

    tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
    payload = json.loads(tool_messages[0]["content"])
    assert payload["error"] == "tool_failed"
    assert "boom" in payload["reason"]


async def test_policy_engine_denial_is_reported_to_the_llm_not_executed():
    """A denied tool call must never reach BaseTool.execute -- the denial
    reason is fed back to the LLM as the tool result instead."""
    tool_call = ToolCall(id="call_1", name="echo", arguments={"text": "hi"})
    provider = _ScriptedProvider([_resp(tool_calls=[tool_call]), _resp("not allowed to do that")])
    service = LLMService([provider])

    result = await run_agent(
        service,
        tools=[_EchoTool()],
        agent_id=_TEST_AGENT_ID,
        policy_engine=_DenyAllPolicyEngine(),
        goal="echo hi",
    )

    tool_messages = [m for m in result["messages"] if m["role"] == "tool"]
    payload = json.loads(tool_messages[0]["content"])
    assert payload == {"error": "denied", "reason": "not permitted"}
    assert result["final_answer"] == "not allowed to do that"


async def test_max_steps_guard_stops_an_infinite_tool_calling_loop():
    service = LLMService([_InfiniteToolCaller()])

    result = await run_agent(
        service,
        tools=[_EchoTool()],
        agent_id=_TEST_AGENT_ID,
        policy_engine=_AllowAllPolicyEngine(),
        goal="loop forever",
        max_steps=3,
    )

    assert result["steps"] == 3
    assert result["stopped_reason"] == "max_steps_reached"
    assert result["final_answer"] is None
