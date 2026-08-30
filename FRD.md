# GovernAI — Functional Requirements Document (FRD)

## Document Control

| Field | Value |
|---|---|
| Project | GovernAI |
| Program | Deloitte Capstone Program 2026 — Manipal University Jaipur — Team Fennec |
| Status | **DRAFT — NOTHING IN THIS DOCUMENT IS FINALIZED** |
| Version | 0.1 |
| Date | 2026-08-19 |
| Companion documents | `PRD.md` (why/business), `SRS.md` (system-level requirements) |

> This FRD breaks each feature named in the SRS down to use-case level: actors, triggers, preconditions, main flow, alternate/exception flows, postconditions, business rules, and acceptance criteria. Items marked 🔶 come from a single source (often one diagram photo) and have not been cross-confirmed elsewhere — treat them as candidate behavior, not committed behavior, until the team signs off.

---

## FRD-01 — User Authentication & RBAC

**Description**: Users log in via Supabase Auth; the backend enforces role-based access on every endpoint.

- **Actors**: Any user (admin, member)
- **Preconditions**: User has an account (Supabase Auth `auth.users` record) linked to a `profiles` row with `role` and `org_id`.
- **Trigger**: User submits login credentials via the Next.js frontend.

**Main flow**:
1. Frontend collects credentials, calls Supabase Auth.
2. Supabase issues a JWT containing `user_id`, `role`, `app_metadata.org_id`.
3. Frontend attaches the JWT as a `Bearer` token on every subsequent API call.
4. FastAPI middleware validates the JWT (via Supabase JWKS endpoint or shared secret) and sets `user_id`/`org_id`/`role` on the request context.
5. RLS policies at the database level reference `auth.uid()`/`auth.jwt()` claims directly for tenant isolation.

**Alternate/exception flows**:
- Invalid/expired JWT → 401, no request context set, request rejected before reaching any domain logic.
- Valid JWT, insufficient role for the requested action → 403.

**Postconditions**: Request proceeds with a known `user_id`/`org_id`/`role`, or is rejected.

**Business rules**:
- Every API endpoint requires authentication except a health-check endpoint.
- `admin`: full CRUD on agents/skills/policies, kill switch, view all audit logs.
- `member`: create/view own agents, view own audit logs.
- 🔶 An earlier version of the role model used four roles (`owner`/`builder`/`auditor`/`admin`) instead of two — not reconciled; see SRS §8.

**Acceptance criteria**:
- Login flow works end-to-end against Supabase Auth.
- An unauthenticated request to any non-health endpoint returns 401.
- A `member` attempting an `admin`-only action (e.g. kill switch on another user's agent) returns 403.

---

## FRD-02 — Agent Creation

**Description**: A user creates a new agent by naming it, describing it, selecting skills, and (implicitly) becoming its owner.

- **Actors**: `admin`, `member`
- **Preconditions**: User is authenticated; at least one skill exists in the registry.
- **Trigger**: User submits the agent creation form (`/agents/new`) or calls `POST /agents/`.

**Main flow**:
1. User provides: name, description, one or more skills.
2. Backend creates an `Agent` row (status `DRAFT`), owned by the requesting user.
3. Backend creates an `AgentPassport` row (`lifecycle_state = DRAFT`).
4. Backend computes the union of `required_permissions` across all selected skills and creates the corresponding `Permission` rows on the passport.
5. Backend synchronously runs the Compliance Check (FRD-03).
6. On pass, passport moves to `APPROVED`; agent may then be activated (by admin or auto-activate, per policy — 🔶 exact activation trigger not finalized).
7. `agent.created` audit event is logged.

**Alternate/exception flows**:
- No skills selected → validation error, agent not created.
- Compliance check fails → agent stays in `DRAFT`, violations returned to the user, `compliance_check.failed` audit event logged.

**Postconditions**: A new Agent + Passport + Permission set exists, with an audit trail of its creation and compliance outcome.

**Business rules**:
- Every agent has exactly one owner.
- An agent's permissions are always the union of its skills' declared permissions — a user cannot grant an agent more than its skills require (no manual over-provisioning in MVP).

**Acceptance criteria**:
- Creating an agent with valid skills results in an `APPROVED` (or activation-ready) passport.
- Creating an agent with no owner, or no skills, fails compliance and stays in `DRAFT`.
- `agent.created` and `compliance_check.passed`/`compliance_check.failed` audit events exist after every attempt.

---

## FRD-03 — Agent Passport & Compliance Check

**Description**: The Passport is the single record the Policy Engine consults on every tool call; the Compliance Check is the deterministic gate an agent must pass before it can act.

- **Actors**: System (automatic), Admin (manual activation/suspension/revocation)
- **Preconditions**: Agent exists in `DRAFT` or is being edited.
- **Trigger**: Agent creation, agent edit (permission change), or explicit "submit for review."

**Main flow (lifecycle)**:
```
DRAFT --submit for review--> COMPLIANCE_CHECK --check passed--> APPROVED
  --admin activates / auto-activate--> ACTIVE
ACTIVE --kill switch / policy violation--> SUSPENDED --admin reactivates--> ACTIVE
ACTIVE --admin permanently revokes--> REVOKED (terminal)
DRAFT <--check failed (fix and resubmit)-- COMPLIANCE_CHECK
```

**Compliance check rules** (deterministic, not an LLM call):
1. Agent has an owner.
2. Agent has at least one skill.
3. Agent's requested permissions are a subset of what its skills require (no over-provisioning).
4. No forbidden permission combination exists.

**Runtime enforcement (every tool call)**:
1. Governance middleware reads the Passport (with a short per-request cache).
2. `lifecycle_state != ACTIVE` → deny immediately.
3. Requested tool's required permission not in the agent's permission set → deny.
4. No applicable policy rule denies → allow.
5. If the passport is modified mid-execution (e.g. suspended), the **next** tool call in that execution picks up the change — no need to interrupt an in-flight LLM call.

**Alternate/exception flows**:
- Passport fetch fails (DB error) → fail-closed, deny.

**Postconditions**: Every tool call has a definitive ALLOW/DENY outcome, logged.

**Business rules**:
- The compliance check is synchronous, deterministic validation logic — never an LLM call.
- Passport records are not immutable, but every change to them is audited.

**Acceptance criteria**:
- An agent with `ticket:read` permission can call `read_ticket` → ALLOW.
- An agent without `ticket:read` calling `read_ticket` → DENY.
- A `SUSPENDED` agent → all tool calls DENY, regardless of its permissions.
- A `REVOKED` agent cannot execute at all.

---

## FRD-04 — Skill Marketplace & Skill-Agent Binding

**Description**: A curated registry of reusable skills that agents are assembled from.

- **Actors**: System (registers skills at startup), Admin/Member (browses/selects skills)
- **Preconditions**: Skills exist as code in the skills directory.
- **Trigger**: Application startup (registration); agent creation flow (selection).

**Main flow**:
1. At startup, the system scans the skills directory; each skill is a class declaring `name`, `display_name`, `description`, `version`, `required_permissions`, `trust_level`, and its tools.
2. Skill metadata is upserted into the `skills` table.
3. During agent creation, the user selects from the registry; each selection creates an `agent_skill` join record.
4. The agent's passport permissions are populated from the union of selected skills' required permissions (see FRD-02).

**MVP skill set** (aligned to the 3-agent direction — see PRD §8/§11 for the scope change from the original 4-skill list):

| Skill | Tools | Permissions | Backs agent |
|---|---|---|---|
| Ticketing | `read_ticket`, `search_tickets`, `create_ticket_reply` | `ticket:read`, `ticket:create` | Ticket Manager |
| Document Search (RAG) | `search_documents`, `get_document` | `docs:search` | RAG agent |
| SQL / Data Query | 🔶 e.g. `run_query` (read-only) | 🔶 e.g. `sql:read` | SQL agent |

🔶 The original architecture doc's third MVP skill was "Code Scanner" (`scan_repository`, `get_file_contents`) — this has been replaced in this FRD by a SQL/Data Query skill to match the current 3-agent roster (Ticket Manager, RAG, SQL). This substitution is a judgment call to keep the FRD internally consistent with the PRD's agent list — **not yet confirmed by the team**.

**Alternate/exception flows**:
- Skill directory scan fails at startup → application should not silently proceed with a stale/empty registry (🔶 exact failure behavior not specified).

**Postconditions**: Skills are queryable via `GET /skills/`; agents can be bound to them.

**Business rules**:
- No dynamic skill upload for MVP — registry is fixed at deploy time.
- All MVP skills use mock adapters (in-memory/seeded data) behind an interface designed so real adapters can be swapped in later without changing the skill's tool signatures.

**Acceptance criteria**:
- All MVP skills are visible in `GET /skills/` with correct metadata and required permissions.
- Creating an agent with the Ticketing + Document Search skills grants exactly `ticket:read`, `ticket:create`, `docs:search` — nothing more.

---

## FRD-05 — Policy Engine & Governance Middleware

**Description**: The enforcement layer that intercepts every tool call and decides ALLOW/DENY.

- **Actors**: System (fully automatic, no human in the loop for MVP evaluation)
- **Preconditions**: Agent has an active execution; LangGraph has selected a tool to call.
- **Trigger**: Every tool call, unconditionally.

**Main flow**:
1. LangGraph node selects a tool → calls `governance_middleware(agent_id, tool_name, tool_args)`.
2. Middleware fetches the Passport; checks `lifecycle_state == ACTIVE`.
3. Middleware calls `policy_engine.evaluate(context)`.
4. Policy Engine loads all enabled `PolicyRule`s ordered by priority; evaluates each against the call context; first DENY wins; no DENY → ALLOW.
5. ALLOW → execute the real tool → log `tool_call.allowed` + result.
6. DENY → return denial reason to the LLM (not a silent failure) → log `tool_call.denied` + reason.
7. Any exception anywhere in this path → treated as DENY, logged as an error.

**Policy rule types (MVP)**:

| Rule type | Behavior | Example config |
|---|---|---|
| `PERMISSION_CHECK` | Deny if agent lacks the permission required by the tool | `{}` (always active) |
| `DENY_LIST` | Deny specific tool+argument combinations | `{"blocked_tools": ["delete_ticket"]}` |
| `RATE_LIMIT` | Deny if agent exceeds N tool calls per minute | `{"max_calls_per_minute": 30}` |

**Alternate/exception flows**:
- Policy Engine raises an exception (e.g. DB unavailable) → fail-closed DENY, never fail-open.

**Postconditions**: Every tool call has exactly one ALLOW/DENY decision and exactly one corresponding audit event.

**Business rules**:
- This is implemented as a decorator/wrapper around every LangGraph tool function — there is no code path for a tool to be invoked without passing through it.
- The governance layer is Python code, never an LLM prompt; the LLM cannot reason its way around it, and injected/malicious content in tool or RAG output cannot itself invoke a tool.

**Acceptance criteria**:
- Two agents, one with permission and one without, attempt the same tool call: one succeeds, one is blocked — demoable live.
- A policy rule denying `delete_ticket` blocks that call even for an agent that otherwise has `ticket:create`/`ticket:read`.
- Simulated Policy Engine failure results in DENY, not ALLOW.

---

## FRD-06 — Agent Runtime / Execution

**Description**: The LangGraph-based (🔶 see SRS §8 on framework choice) execution loop that lets an agent reason over a goal and call tools.

- **Actors**: Agent (via LLM), triggered by a user or the system
- **Preconditions**: Agent is `ACTIVE`.
- **Trigger**: `POST /agents/{id}/execute` with a goal.

**Main flow**:
1. API creates an `Execution` record (`status = RUNNING`).
2. LangGraph graph is compiled with the agent's bound tools, each wrapped in governance middleware.
3. Graph runs asynchronously: LLM reasons → selects a tool (or decides it's done) → governance check → execute or deny → result fed back to LLM → repeat.
4. Each step creates an `ExecutionStep` record.
5. Steps are streamed to the frontend via SSE as they happen.
6. On completion, `Execution.status` is set to `COMPLETED` or `FAILED`.

**Alternate/exception flows**:
- LLM call fails/times out → retry with backoff (same provider, exponential, max 2 attempts) → fall back to secondary provider → retry → if still failing, execution fails gracefully, failure chain recorded in the audit log.
- A tool call is denied and the LLM cannot proceed → execution ends (not necessarily a hard failure — the LLM may report the denial as its answer).
- Kill switch mid-execution → next governance check returns DENY with a suspension message → LangGraph exits gracefully; hard-cancel of the asyncio task is the fallback if graceful exit exceeds a 30s timeout.
- Process crash mid-execution → LangGraph's checkpointer (Postgres-backed 🔶) allows resumption, or the execution is marked `FAILED`.

**Postconditions**: Execution reaches a terminal status; every step, tool call, and cost is recorded.

**Business rules**:
- LLM retries never re-invoke a tool that already executed successfully — only the LLM call is retried; tool results are preserved in state.
- A hard limit on execution steps (🔶 e.g. default 20, per one architecture-diagram image on threat mitigation) prevents runaway/excessive-agency loops — exact default not confirmed elsewhere.

**Acceptance criteria**:
- An agent given a goal produces at least one tool call and a final result, or a clean failure/denial with a reason.
- SSE stream shows steps in real time during a live execution.
- Killing an agent mid-execution stops it within one tool-call cycle.

---

## FRD-07 — Ticket Manager Agent

**Description**: Reads a ticket and drafts/takes an action on it, using the Ticketing skill.

- **Actors**: Agent (Ticket Manager), triggered by a user goal (e.g. "resolve ticket #123")
- **Preconditions**: Agent bound to the Ticketing skill; has `ticket:read` (and `ticket:create` if drafting a reply).

**Main flow**:
1. Given a goal referencing a ticket, the agent calls `read_ticket`/`search_tickets` (governance-checked).
2. Agent reasons over the ticket content and drafts a response or action.
3. Agent calls `create_ticket_reply` (governance-checked) to submit the action, if permitted.

🔶 **Candidate stretch feature — not confirmed**: a manual-approval vs. fully-automated mode toggle, described in the original project write-up as doubling as a live human-in-the-loop / policy-gate demo. If implemented: in manual mode, the drafted action pauses for explicit user approval before `create_ticket_reply` executes; in automated mode, it executes directly (still governance-checked).

**Alternate/exception flows**:
- Agent lacks `ticket:create` → drafting succeeds but the create-reply call is denied; agent must report this rather than silently failing.
- Ticket not found (mock adapter returns not-found) → agent reports inability to proceed.

**Postconditions**: A ticket has a drafted/submitted reply (mock adapter, MVP), and the full tool-call chain is audited and costed.

**Acceptance criteria**:
- Given a seeded mock ticket, the agent reads it and produces a relevant drafted reply.
- An unauthorized attempt to reply (agent lacking `ticket:create`) is blocked and visible in the audit log as a DENY.

---

## FRD-08 — RAG (Document Search) Agent

**Description**: Retrieves and answers questions grounded in internal documents.

- **Actors**: Agent (RAG), triggered by a user goal/question
- **Preconditions**: Agent bound to the Document Search skill; has `docs:search`; at least one document has been ingested.

**Main flow (ingestion, one-time per document)**:
1. Document uploaded → parsed (PDF/Markdown/plain text) → chunked (🔶 fixed-size ~512 tokens, 50-token overlap, per the main architecture doc) → embedded (🔶 Gemini `text-embedding-004` or similar free model) → chunks + embeddings stored in `document_chunks` (pgvector); document metadata stored in `documents`, including an `access_scope` (array of permission strings).

**Main flow (query, per execution)**:
1. Agent calls `search_documents` with the user's question (governance-checked: requires `docs:search`).
2. The tool issues a **pre-filtered** SQL query: vector similarity search joined to `documents`, filtered by `org_id` and `access_scope && agent_permissions` (array overlap), **before** ranking by similarity — never filtered after the fact.
3. Top-N chunks returned to the LLM as context; LLM composes a grounded answer.

🔶 **Candidate enhancement — single-source, not confirmed**: hybrid pgvector + full-text-search with RRF fusion, contextual chunk prepending, a reranking step (Cohere Rerank or a local reranker), and a CRAG-style self-correction loop. This appears only in one architecture-diagram image and is materially more complex than the documented pipeline above — treat as a stretch goal pending an explicit scope decision.

**Alternate/exception flows**:
- No matching chunks within the agent's access scope → agent reports it cannot find relevant information, rather than fabricating an answer (LLM output should be explicitly instructed not to answer beyond retrieved context).
- Vector search fails → tool returns an error; agent can still use other tools if applicable.

**Postconditions**: An answer is produced (or a documented "not found"), grounded only in chunks the agent was authorized to see.

**Business rules**:
- Pre-filtering (not post-filtering) is a hard requirement — the rationale recorded in source material is that post-filtering is a security risk (the vector search might surface forbidden content in intermediate results before any filter runs, and any filter bug would leak data).

**Acceptance criteria**:
- Uploading an internal doc and asking a question the agent is authorized to see produces a grounded answer citing that content.
- An agent without `docs:search`, or without the relevant `access_scope`, retrieves nothing from a restricted document — demoable live as a negative test.

---

## FRD-09 — SQL Agent

**Description**: Answers questions over structured data (Excel/CSV/SQL) via scoped, read-only queries — not naive text embedding, since numeric data needs computation.

- **Actors**: Agent (SQL), triggered by a user goal/question
- **Preconditions**: Agent bound to the SQL/Data Query skill; has the relevant read permission; a target dataset/table is accessible.

**Main flow** 🔶 (this flow is inferred from the general project description plus one diagram image; it has not been separately written out in the architecture planning doc's prose, so treat the specifics as a proposal):
1. Agent receives a natural-language question requiring structured-data lookup/computation.
2. Agent (or a deterministic translation step) produces a SQL query scoped to permitted tables/columns.
3. Before execution, the query is validated — 🔶 candidate approach: parse to an AST (e.g. via `sqlglot`) to confirm it is read-only (no `INSERT`/`UPDATE`/`DELETE`/`DDL`) and touches only permitted tables.
4. Query executes against a **read-only** database role, with a timeout.
5. Result set returned to the LLM, which composes a natural-language answer.

**Alternate/exception flows**:
- Query fails validation (write/DDL detected, or out-of-scope table) → denied before execution, logged as a policy denial, not silently rewritten.
- Query times out → error surfaced to the LLM as a tool failure.

**Postconditions**: A read-only query executed (or was blocked), fully audited and costed like any other tool call.

**Business rules**:
- The SQL agent must never be able to write, alter schema, or query outside its declared scope, regardless of what the LLM "believes" it should do — enforcement happens in the query-validation/execution layer, not in the prompt.

**Acceptance criteria**:
- A well-scoped question returns a correct, computed answer (not a hallucinated one) from seeded structured data.
- An attempted write or out-of-scope query is blocked before it reaches the database, and this is visible in the audit log.

---

## FRD-10 — Audit Log

**Description**: An unconditional, append-only record of every significant system action.

- **Actors**: System (writer, always), Admin/Member (reader, via dashboard/API)
- **Preconditions**: None — logging happens regardless of outcome.

**Events logged** (actor / key fields):

| Action | Actor | Key fields |
|---|---|---|
| `agent.created` | USER | agent_id, agent_name, owner_id |
| `agent.activated` | USER/SYSTEM | agent_id |
| `agent.suspended` | USER | agent_id, reason |
| `agent.revoked` | USER | agent_id, reason |
| `agent.permissions_changed` | USER | agent_id, old_permissions, new_permissions |
| `execution.started` | AGENT | agent_id, execution_id, goal |
| `execution.completed` | AGENT | agent_id, execution_id, result |
| `execution.failed` | AGENT | agent_id, execution_id, error |
| `tool_call.allowed` | AGENT | agent_id, execution_id, tool, policy_decision |
| `tool_call.denied` | AGENT | agent_id, execution_id, tool, policy_decision, reason |
| `tool_call.failed` | AGENT | agent_id, execution_id, tool, error |
| `llm_call` | SYSTEM | agent_id, execution_id, model, tokens, cost |
| `kill_switch.activated` | USER | agent_id, activated_by |
| `compliance_check.passed` | SYSTEM | agent_id |
| `compliance_check.failed` | SYSTEM | agent_id, violations |

**Main flow**: Every governed action, on completion (success or failure), writes exactly one `AuditEvent` row with a server-generated timestamp (never client-supplied).

**Business rules**:
- Append-only: the application's database role has `INSERT`/`SELECT` only on `audit_events` — no `UPDATE`/`DELETE`, enforced at the database (not application) level.
- A composite index on `(agent_id, timestamp)` and a BRIN index on `timestamp` support efficient per-agent and time-range queries.

**Acceptance criteria**:
- Executing an agent end-to-end produces a complete, filterable audit trail covering every tool call (allowed and denied) and the execution's overall outcome.
- Attempting to update or delete an audit row via the application's DB role fails (privilege error), demoable directly against the database.

---

## FRD-11 — Cost Tracking & Budget Cap (USP)

**Description**: Real-time, per-agent cost attribution with an enforced budget cap — the platform's headline differentiator. **Confirmed as the project's USP.**

- **Actors**: System (records costs automatically), Admin (sets/adjusts budget caps — 🔶 exact UI/API for setting a cap not yet specified)
- **Preconditions**: An LLM or billable tool call occurs.

**Main flow**:
1. Every LLM response includes token usage (prompt/completion/total).
2. A configurable pricing table (loaded from env/config, never hardcoded — model pricing changes too often for that) maps `model → {input, output}` cost per 1K tokens.
3. A `CostEvent` is written: agent_id, execution_id, execution_step_id, event_type (`LLM_CALL`/`TOOL_CALL`), model, provider, token counts, `cost_usd`, timestamp.
4. Before each call, the Policy Engine (or a cost-specific check alongside it) verifies the agent's accumulated cost is still under its budget cap.
5. If the cap would be exceeded, the call is denied and the agent is automatically transitioned to a paused/suspended state; this is itself an audited event.
6. Dashboard aggregates costs live: total per agent, breakdown by model, breakdown by execution — via straightforward `SUM(cost_usd) ... GROUP BY ...` queries (no materialized views needed at demo scale).
7. Cost updates are pushed to the dashboard in real time via SSE (`cost_update` events).

**Alternate/exception flows**:
- Tool calls that hit external APIs (not LLM calls) use a fixed or estimated cost, still logged as a `CostEvent`.

**Postconditions**: Every dollar of simulated spend is attributable to a specific agent, execution, and model; an over-budget agent is demonstrably auto-paused.

**Business rules**:
- Cost calculation is deterministic and config-driven, never hardcoded per-model logic in application code.
- This is a **platform capability**, not a standalone agent — 🔶 the original architecture doc proposed a dedicated "cost/budget-analyst agent" that would query the platform's own audit/cost logs; current direction (this conversation) does not include that as a 4th agent. The capability itself (tracking + cap + auto-pause + dashboard) remains fully in scope as the USP.

**Acceptance criteria**:
- Running an agent's execution produces cost events matching the actual token usage and configured pricing.
- Setting a low budget cap and running an agent past it results in a visible, automatic pause, logged and reflected on the dashboard in real time.
- Cost dashboard correctly aggregates spend per agent and per model.

---

## FRD-12 — Kill Switch / Agent Lifecycle Control

**Description**: Instant, admin-triggered suspension of a running or idle agent.

- **Actors**: Admin
- **Preconditions**: Agent exists (any state other than `REVOKED`).
- **Trigger**: Admin clicks "Kill" in the dashboard, or `POST /agents/{id}/kill`.

**Main flow**:
1. Backend sets `Agent.status = SUSPENDED` and `AgentPassport.lifecycle_state = SUSPENDED` in a single transaction.
2. An `AuditEvent` (`kill_switch.activated`) is created, including who triggered it.
3. If the agent has a running execution, the **next** governance middleware check (which runs before every tool call) reads the updated state and returns DENY.
4. The LLM receives a message that the agent has been suspended; the LangGraph execution exits gracefully; execution status is set to `TERMINATED`.
5. An agent cannot restart automatically — an admin must explicitly call `POST /agents/{id}/reactivate`, which also creates an audit event.

**Alternate/exception flows**:
- Graceful exit doesn't happen within a timeout (🔶 30s, per the architecture doc) → hard-cancel of the underlying async task as a fallback.

**Postconditions**: Agent is `SUSPENDED`; any running execution has stopped; the action is fully audited.

**Business rules**:
- Propagation is sub-second for the *next* tool call; an LLM call already in flight is not interrupted mid-call — accepted as adequate for MVP.

**Acceptance criteria**:
- Killing an active agent with a running execution stops it within one tool-call cycle, visibly on the live dashboard.
- A killed agent cannot execute again until explicitly reactivated by an admin.

---

## FRD-13 — Real-Time Dashboard

**Description**: The live operational view for leadership/admins.

- **Actors**: Admin, Member (own agents)
- **Preconditions**: User authenticated.

**Main flow**:
1. Initial page load fetches server-rendered data (agent list, cost summaries) for fast first paint.
2. Client subscribes to `GET /api/v1/events/stream` (global) or `.../stream?agent_id={id}` (per-agent) via SSE.
3. As events arrive (`agent_status`, `execution_step`, `policy_decision`, `cost_update`, `kill_switch`, `error`), the relevant UI updates without a page reload.
4. Mutations (kill switch, agent creation, policy toggles) are ordinary REST calls; the resulting state change is then reflected back via the next SSE event.

**Alternate/exception flows**:
- SSE connection drops → browser's EventSource auto-reconnects; any events missed during the gap can be recovered via a REST fetch.

**Postconditions**: The dashboard accurately reflects live system state at all times during normal operation.

**Acceptance criteria**:
- A full demo sequence — create agent, execute, monitor live, kill, view audit trail, view cost — is achievable without a manual page refresh at any point.

---

## FRD-14 — Policy Management UI

**Description**: Admin-facing view to list, create, and toggle policy rules.

- **Actors**: Admin
- **Preconditions**: User is `admin`.

**Main flow**:
1. Admin views `/policies` — list of policies and their rules.
2. Admin can create a new policy/rule (name, rule_type, config, priority, enabled).
3. Admin can enable/disable a rule without a redeployment — the Policy Engine picks up the change on the next evaluation (rules are database records, not compiled code).

**Postconditions**: Policy changes take effect on the very next tool-call evaluation across the system.

**Acceptance criteria**:
- Toggling a `DENY_LIST` rule off/on visibly changes the ALLOW/DENY outcome for a subsequent identical tool call, without restarting the backend.

---

## Appendix — Cross-Reference of Open Items

All 🔶-flagged items in this document map to the consolidated Open Questions list in `PRD.md` §11 and `SRS.md` §8. This FRD deliberately keeps them inline (rather than only in an appendix) so each one is visible exactly where it affects a specific feature's behavior.
