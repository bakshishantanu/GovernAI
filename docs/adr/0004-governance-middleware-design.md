# ADR 0004: Fail-Closed Governance Middleware Design

## Context
Agents in GovernAI are capable of executing potentially destructive actions (e.g., executing SQL queries, calling external APIs). The core value proposition of GovernAI is ensuring these agents act safely. We needed a mechanism to intercept and evaluate every action an agent attempts *before* it happens.

## Decision
We implemented a **Fail-Closed Governance Middleware (`PolicyEngine`)** that is deeply integrated into the LangGraph execution loop (`agent_graph.py`).

## Rationale
1. **Fail-Closed Default:** If a tool requires a permission that the agent lacks, or if an overarching policy (e.g., budget limits) evaluates to false, the system automatically denies the action. The burden of proof is on the policy engine to explicitly `ALLOW`.
2. **Graph Injection:** By injecting the `PolicyEngine` into the LangGraph state graph at the `tools_node`, we guarantee that *no tool* can be executed without passing through the governance evaluation.
3. **LLM Feedback Loop:** Instead of crashing the execution when a policy is violated, the middleware returns a structured `DENIED` error back to the LLM's context window. This allows the LLM to understand *why* it was blocked and potentially adjust its reasoning or choose a different, approved tool.

## Consequences
- Every new tool must explicitly declare its `required_permission` attribute.
- The `agent_graph.py` is permanently coupled to the `PolicyEngine`.
