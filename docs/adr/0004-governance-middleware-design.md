# ADR 0004: Fail-Closed Governance Middleware Design

## Context
Agents in GovernAI are capable of executing potentially destructive actions (e.g., executing SQL queries, calling external APIs). The core value proposition of GovernAI is ensuring these agents act safely. We needed a mechanism to intercept and evaluate every action an agent attempts *before* it happens.

## Decision
We implemented a **Fail-Closed Governance Middleware** — `govern_tool()` in `app/domain/governance/middleware.py` — that every LangGraph tool call passes through (`agent_graph.py`'s `tools_node`).

## Rationale
1. **Fail-Closed Default:** If a tool requires a permission the agent lacks, or if an overarching policy (e.g., budget limits) evaluates to false, the system automatically denies the action. The burden of proof is on the policy engine to explicitly `ALLOW`.
2. **Wrapper, not inline:** `govern_tool()` wraps policy evaluation, timed execution, and audit logging as one standalone function that `tools_node` calls for every resolved tool — matching Contract 4's original `govern_tool()` shape (a wrapper around every tool call) rather than being written inline inside the graph. This makes the gate independently unit-testable (`tests/domain/governance/test_middleware.py`) without standing up the LangGraph loop, and keeps `tools_node` from being the only place the guarantee "no tool executes ungoverned" can be verified.
3. **LLM Feedback Loop:** Instead of crashing the execution when a policy is violated, `govern_tool()` returns a structured `DENIED` error back to the LLM's context window. This allows the LLM to understand *why* it was blocked and potentially adjust its reasoning or choose a different, approved tool.

## Consequences
- Every new tool must explicitly declare its `required_permission` attribute.
- `tools_node` depends on `govern_tool()`, not directly on `PolicyEngine` — the policy/audit/timeout wiring lives in one place, reusable by any future caller (e.g., a non-LangGraph execution path) without duplicating the check.

## History
- Originally implemented as an inline check inside `tools_node`, calling `PolicyEngine.evaluate()` directly. Extracted into the standalone `govern_tool()` wrapper (this decision) once the inline form was found to block task #38 (governance integration tests) — it couldn't be exercised without the full LangGraph graph — and to bring the code in line with Contract 4's original wrapper-function design. Pure refactor: no behavior change.
