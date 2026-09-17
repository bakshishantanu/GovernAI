from __future__ import annotations

import json
import operator
from typing import Annotated, TypedDict
from uuid import UUID

from langgraph.graph import END, StateGraph

from app.domain.audit.service import AuditService
from app.domain.costs.service import CostService
from app.domain.governance.budget import BudgetGuard
from app.domain.governance.middleware import govern_tool
from app.domain.policies.engine import PolicyEngine
from app.runtime.llm.base import ToolCall
from app.runtime.llm.service import LLMService
from app.skills.base import BaseTool

TOOL_EXECUTION_TIMEOUT_SECONDS = 30.0


def _json_default(obj: object) -> object:
    # Tool results can carry numpy scalars (e.g. a similarity/relevance
    # score) that json.dumps doesn't know how to encode; numpy scalars all
    # expose .item() to unwrap to the equivalent native Python type.
    to_native = getattr(obj, "item", None)
    if callable(to_native):
        return to_native()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    steps: int
    max_steps: int
    stopped_reason: str | None


def _to_openai_tool_call(tc: ToolCall) -> dict:
    return {
        "id": tc.id,
        "type": "function",
        "function": {"name": tc.name, "arguments": json.dumps(tc.arguments)},
    }


def build_agent_graph(
    llm_service: LLMService,
    tools: list[BaseTool],
    agent_id: UUID,
    org_id: UUID,
    execution_id: UUID,
    policy_engine: PolicyEngine,
    audit_service: AuditService,
    cost_service: CostService,
    budget_guard: BudgetGuard | None = None,
):
    """Builds the security-hardened agent reasoning loop."""
    tools_by_name = {tool.name: tool for tool in tools}
    tool_specs = [tool.to_openai_tool() for tool in tools]

    async def agent_node(state: AgentState) -> dict:
        # BUDGET GATE: the LLM call is the dominant cost driver, so it must be
        # checked before it happens -- not just before tool calls, which is
        # where this used to live exclusively. Without this, an agent that is
        # already over budget (or never calls a tool at all) could keep
        # making billable LLM calls indefinitely.
        if budget_guard is not None:
            budget = await budget_guard.check(agent_id, org_id)
            if not budget.allowed:
                await audit_service.log_tool_call(
                    org_id, agent_id, execution_id, "llm_call", False, budget.reason
                )
                return {
                    "messages": [{"role": "assistant", "content": budget.reason}],
                    "steps": state["steps"] + 1,
                    "stopped_reason": "budget_exceeded",
                }

        response = await llm_service.chat(state["messages"], tools=tool_specs)

        # 💰 COST TRACKING: Record token usage per LLM call
        was_priced = True
        if response.usage:
            was_priced = await cost_service.record_llm_cost(
                org_id=org_id,
                agent_id=agent_id,
                execution_id=execution_id,
                model=response.model,
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
            )

        # FAIL CLOSED: a call that just happened on an unpriced model spent
        # real money nothing can put a cap on, since BudgetGuard only ever
        # sees priced spend. This can't undo that one call, but it stops the
        # agent from making another one -- same as a real budget breach.
        if not was_priced and budget_guard is not None:
            budget = await budget_guard.deny_unpriced_model(agent_id, org_id, response.model)
            await audit_service.log_tool_call(
                org_id, agent_id, execution_id, "llm_call", False, budget.reason
            )
            return {
                "messages": [{"role": "assistant", "content": budget.reason}],
                "steps": state["steps"] + 1,
                "stopped_reason": "unpriced_model",
            }

        assistant_message: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            assistant_message["tool_calls"] = [
                _to_openai_tool_call(tc) for tc in response.tool_calls
            ]

        return {"messages": [assistant_message], "steps": state["steps"] + 1}

    async def tools_node(state: AgentState) -> dict:
        last_message = state["messages"][-1]
        tool_calls = last_message.get("tool_calls", [])

        results = []
        for raw_call in tool_calls:
            name = raw_call["function"]["name"]
            arguments = json.loads(raw_call["function"]["arguments"])
            tool_call_id = raw_call["id"]

            tool = tools_by_name.get(name)
            if tool is None:
                result = {"error": "unknown_tool", "reason": f"no tool named '{name}' is available"}
                await audit_service.log_tool_call(
                    org_id, agent_id, execution_id, name, False, "Unknown tool"
                )
            else:
                # Let the tool fill in anything the model left out using
                # earlier tool results in this execution (see BaseTool.enrich_arguments).
                arguments = tool.enrich_arguments(arguments, state["messages"])
                # GOVERNANCE GATE: policy check + timed execution + audit log,
                # for every tool call, allowed or denied.
                result = await govern_tool(
                    policy_engine=policy_engine,
                    audit_service=audit_service,
                    org_id=org_id,
                    agent_id=agent_id,
                    execution_id=execution_id,
                    tool=tool,
                    arguments=arguments,
                    timeout_seconds=TOOL_EXECUTION_TIMEOUT_SECONDS,
                    budget_guard=budget_guard,
                )

            results.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": json.dumps(result, default=_json_default),
                }
            )

        return {"messages": results}

    def route_after_agent(state: AgentState) -> str:
        if state["steps"] >= state["max_steps"]:
            return "max_steps"
        last_message = state["messages"][-1]
        if last_message.get("tool_calls"):
            return "tools"
        return "done"

    builder = StateGraph(AgentState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", tools_node)
    builder.set_entry_point("agent")
    builder.add_conditional_edges(
        "agent",
        route_after_agent,
        {"tools": "tools", "done": END, "max_steps": END},
    )
    builder.add_edge("tools", "agent")

    return builder.compile()


async def run_agent(
    llm_service: LLMService,
    tools: list[BaseTool],
    agent_id: UUID,
    org_id: UUID,
    execution_id: UUID,
    policy_engine: PolicyEngine,
    audit_service: AuditService,
    cost_service: CostService,
    goal: str,
    system_prompt: str | None = None,
    max_steps: int = 10,
    budget_guard: BudgetGuard | None = None,
) -> dict:
    """Run a goal through the security-hardened agent graph."""
    graph = build_agent_graph(
        llm_service,
        tools,
        agent_id,
        org_id,
        execution_id,
        policy_engine,
        audit_service,
        cost_service,
        budget_guard,
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": goal})

    final_state = await graph.ainvoke(
        {"messages": messages, "steps": 0, "max_steps": max_steps, "stopped_reason": None}
    )

    # agent_node sets stopped_reason itself when it stops the run early
    # (budget exceeded, or an unpriced model denied); that always takes
    # precedence over inferring max_steps/completed from the last message.
    early_stop = final_state.get("stopped_reason")
    hit_max_steps = final_state["steps"] >= max_steps and final_state["messages"][-1].get(
        "tool_calls"
    )
    final_message = final_state["messages"][-1]

    if early_stop:
        stopped_reason = early_stop
    elif hit_max_steps:
        stopped_reason = "max_steps_reached"
    else:
        stopped_reason = "completed"

    return {
        "final_answer": None if (early_stop or hit_max_steps) else final_message.get("content"),
        "messages": final_state["messages"],
        "steps": final_state["steps"],
        "stopped_reason": stopped_reason,
    }
