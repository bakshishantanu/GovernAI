import json
import operator
from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph

from app.runtime.llm.base import ToolCall
from app.runtime.llm.service import LLMService
from app.skills.base import BaseTool
from uuid import UUID
from app.domain.policies.engine import PolicyEngine


class AgentState(TypedDict):
    messages: Annotated[list[dict], operator.add]
    steps: int
    max_steps: int
    stopped_reason: str | None


def build_agent_graph(
    llm_service: LLMService, 
    tools: list[BaseTool],
    agent_id: UUID,
    policy_engine: PolicyEngine
):
    """Builds the basic agent reasoning loop (FRD-06): LLM reasons -> selects
    a tool (or finishes) -> tool executes -> result fed back -> repeat.

    This graph integrates the PolicyEngine to intercept and evaluate every
    tool call against the agent's permissions. Denied tool calls return 
    the denial reason to the LLM.
    """
    tools_by_name = {tool.name: tool for tool in tools}
    tool_specs = [tool.to_openai_tool() for tool in tools]

    async def agent_node(state: AgentState) -> dict:
        response = await llm_service.chat(state["messages"], tools=tool_specs)

        assistant_message: dict = {"role": "assistant", "content": response.content}
        if response.tool_calls:
            assistant_message["tool_calls"] = [_to_openai_tool_call(tc) for tc in response.tool_calls]

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
            else:
                try:
                    decision = await policy_engine.evaluate(
                        agent_id=agent_id,
                        tool_name=tool.name,
                        tool_args=arguments,
                        required_permission=getattr(tool, "required_permission", "")
                    )
                    if not decision.allowed:
                        result = {"error": "denied", "reason": decision.reason}
                    else:
                        result = await tool.execute(**arguments)
                except Exception as exc:  # a tool must never crash the whole run
                    result = {"error": "tool_failed", "reason": str(exc)}

            results.append({"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(result)})

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
    policy_engine: PolicyEngine,
    goal: str,
    system_prompt: str | None = None,
    max_steps: int = 10,
) -> dict:
    """Convenience wrapper: run a goal through the agent graph to completion
    (or until max_steps is hit) and return the final answer plus full
    transcript.
    """
    graph = build_agent_graph(llm_service, tools, agent_id, policy_engine)

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": goal})

    final_state = await graph.ainvoke({"messages": messages, "steps": 0, "max_steps": max_steps, "stopped_reason": None})

    hit_max_steps = final_state["steps"] >= max_steps and final_state["messages"][-1].get("tool_calls")
    final_message = final_state["messages"][-1]

    return {
        "final_answer": None if hit_max_steps else final_message.get("content"),
        "messages": final_state["messages"],
        "steps": final_state["steps"],
        "stopped_reason": "max_steps_reached" if hit_max_steps else "completed",
    }


def _to_openai_tool_call(tool_call: ToolCall) -> dict:
    return {
        "id": tool_call.id,
        "type": "function",
        "function": {"name": tool_call.name, "arguments": json.dumps(tool_call.arguments)},
    }
