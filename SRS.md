# GovernAI — Software Requirements Specification (SRS)

## Document Control

| Field | Value |
|---|---|
| Project | GovernAI |
| Program | Deloitte Capstone Program 2026 — Manipal University Jaipur — Team Fennec |
| Status | **DRAFT — NOTHING IN THIS DOCUMENT IS FINALIZED** |
| Version | 0.1 |
| Date | 2026-08-19 |
| Companion documents | `PRD.md` (business/product requirements), `FRD.md` (feature-level functional specs) |

> This SRS follows a standard structure (loosely IEEE 830-style: Introduction → Overall Description → External Interfaces → Functional Requirements → Non-Functional Requirements → Data Requirements). Every technical decision recorded here is drawn from the team's architecture-planning notes and diagrams; where those notes conflict with each other or with the original project description, this is flagged inline with 🔶 and consolidated in §8 (Open Questions). Per explicit instruction, none of this is to be treated as locked.

---

## 1. Introduction

### 1.1 Purpose

This SRS specifies the software requirements for GovernAI: a platform that lets builders assemble AI agents from reusable "skills," and automatically wraps every agent with an identity, a permission scope, and a live cost budget enforced by a Policy Engine at every tool call.

### 1.2 Scope

Covers the backend (FastAPI), frontend (Next.js dashboard), agent runtime (LangGraph 🔶 — see §8), governance middleware/policy engine, skill marketplace, and the three MVP agents (Ticket Manager, RAG, SQL). Excludes multi-tenant production hardening, real external system integrations (MVP uses mock adapters), and billing.

### 1.3 Definitions & Acronyms

| Term | Meaning |
|---|---|
| **Agent** | An AI entity registered in the system, assembled from one or more skills, governed by its own Passport. |
| **Skill** | A reusable capability bundle (metadata + permissions + 1 or more tools), e.g. "Ticketing." |
| **Tool** | A single callable function within a skill, e.g. `read_ticket(ticket_id)`. |
| **Agent Passport** | A database record consolidating an agent's identity, permission set, compliance status, and lifecycle state — the object the Policy Engine consults on every tool call. |
| **Policy Engine** | The rule-evaluation component that decides ALLOW/DENY for a given tool call. |
| **Governance Middleware** | The interception layer wrapping every LangGraph tool; calls the Policy Engine before the real tool function runs. |
| **Execution** | One run of an agent processing a goal, made up of one or more Execution Steps. |
| **Audit Event** | An immutable, append-only log entry recording one significant action (agent lifecycle change, tool call, LLM call, kill switch, etc.). |
| **Cost Event** | An immutable log entry recording token usage/cost for a single LLM or tool call. |
| **RLS** | Row-Level Security (Postgres). |
| **RBAC** | Role-Based Access Control. |
| **SSE** | Server-Sent Events. |

### 1.4 References

- Deloitte Capstone 2026 Expression of Interest deck (team Fennec submission)
- Internal architecture planning notes ("GovernAI — Architecture & Implementation Plan," 50 pages)
- Architecture/tech-stack diagram photographs (3 images, team whiteboard/notes)

### 1.5 Overview

§2 describes the system at a high level. §3 defines external interfaces. §4 is the full functional requirements list. §5 is non-functional requirements. §6 covers data requirements. §7 covers other constraints. §8 lists unresolved conflicts across source material.

---

## 2. Overall Description

### 2.1 Product Perspective

GovernAI is a new, standalone platform (not an extension of an existing product). It sits **alongside** existing enterprise systems (ticketing, doc stores, databases) via connectors ("skills"), rather than replacing them.

### 2.2 System Architecture — Six Modules

| # | Module | Responsibility |
|---|---|---|
| 1 | **Dashboard** (Next.js) | Live view of every agent: status, actions, cost, kill switch |
| 2 | **API / Backend** (FastAPI) | Auth, business logic, DB access, REST/SSE endpoints |
| 3 | **Skill Marketplace** | Catalog of reusable connectors, each declaring required permissions |
| 4 | **Agent Definition Layer** | Per-agent custom logic: which skills to call, in what order, with what prompts/rules |
| 5 | **Agent Runtime** (LangGraph 🔶) | Executes the graph defined by module 4 |
| 6 | **Passport / Policy Engine** | Per-agent identity, permission scope, cost budget; intercepts every tool call; logs unconditionally |

### 2.3 High-Level Component Flow

```
Frontend (Next.js, Vercel)
  → REST + SSE →
Backend (FastAPI, Railway)
  → FastAPI API layer → Agent Service → LangGraph Runtime
       → LLM Provider Abstraction → [Groq primary, Gemini 2.5 Flash fallback]
       → tool call → Governance Middleware
            → Policy Engine (evaluate permissions + policy rules)
            → Agent Passport (lifecycle_state, permissions)
            → ALLOW → Skills Layer (mock adapters, MVP) → Audit Event + Cost Event
            → DENY  → Audit Event (denied + reason), no tool execution
  → PostgreSQL + pgvector (Supabase) — single source of truth for all of the above
```

### 2.4 Sequence — Agent Creation → Execution → Governance Check (narrative)

1. Admin creates an agent via the dashboard, selecting skills.
2. Backend validates the JWT, creates the Agent + Passport + Permissions records.
3. A synchronous, deterministic **compliance check** runs (not an LLM call) — see FR-3.
4. On pass, the agent becomes `ACTIVE`. Admin triggers execution with a goal.
5. LangGraph runs; on each tool selection, Governance Middleware fetches the Passport, evaluates permissions + policy rules, and returns ALLOW/DENY.
6. ALLOW → tool executes → result returned to LLM → Audit Event (`tool_call.allowed`) + Cost Event written.
7. DENY → LLM receives a denial message, no execution → Audit Event (`tool_call.denied`) written.
8. Execution completes; status updated; all steps were streamed to the dashboard via SSE as they happened.

### 2.5 User Classes

| Role | Capabilities |
|---|---|
| `admin` | Full CRUD on agents, skills, policies; kill switch; view all audit logs |
| `member` | Create agents (own), view own agents, view own audit logs |

🔶 The original project description also names `owner`, `builder`, and `auditor` roles distinct from `admin`/`member`. The architecture planning doc collapses this to just `admin`/`member`. **Not reconciled** — see §8.

### 2.6 Operating Environment

- Frontend: Vercel (Next.js 16, App Router, TypeScript strict)
- Backend: Railway (FastAPI, Python 3.12+)
- Database: Supabase (PostgreSQL + pgvector + RLS)
- Single-organization deployment for MVP; schema is multi-tenant-*ready* (every tenant-scoped table carries `organization_id`) but not multi-tenant-*active*.

### 2.7 Design & Implementation Constraints

- Governance is enforced in Python code (the middleware), never as an LLM instruction/prompt — the LLM cannot reason its way around it.
- Fail-closed: if the Policy Engine errors (DB down, unexpected exception), the default is DENY.
- Model names and pricing are configuration, not hardcoded — both LLM providers have changed model lineups multiple times in under a year.
- All database access goes through repository classes — no raw SQL in service/business logic (prevents SQL injection, keeps queries auditable).
- Audit event table (`audit_events`): the application's database role has `INSERT`/`SELECT` only — no `UPDATE`/`DELETE`, enforced at the database level.

### 2.8 Assumptions & Dependencies

- Enterprise already has basic cloud/API access and sanctioned data sources.
- Agents only ever reach real systems through approved skills — never raw, unmonitored access.
- Free-tier availability of Groq and Gemini APIs is sufficient for build and demo (with fallback/circuit-breaker as mitigation).

---

## 3. External Interface Requirements

### 3.1 User Interface

Next.js dashboard pages (🔶 route list per architecture doc; not yet built/validated):

| Route | Purpose |
|---|---|
| `/` | Dashboard: agent overview, cost summary, recent activity |
| `/agents` | Agent list with status, cost, owner |
| `/agents/new` | Agent creation wizard (name, skills, owner) |
| `/agents/[id]` | Agent details: passport, permissions, executions, cost |
| `/agents/[id]/executions/[eid]` | Live execution view: steps, tool calls, policy decisions (SSE) |
| `/skills` | Skill marketplace: available skills, descriptions, trust levels |
| `/audit` | Audit log viewer: filterable, paginated |
| `/costs` | Cost dashboard: charts, breakdowns, trends |
| `/policies` | Policy management: list, create, enable/disable rules |
| `/settings` | Org settings, user management |

### 3.2 API Interface

Base path `/api/v1/`. Standards: Pydantic v2 request/response models with a consistent envelope (`{ data, meta?, errors? }`); RFC 7807 problem-details error format; Bearer JWT (Supabase Auth) in the `Authorization` header; cursor-based pagination for high-volume audit logs, offset-based elsewhere.

| Resource | Methods | Purpose |
|---|---|---|
| `/agents/` | GET, POST | List / create agents |
| `/agents/{id}` | GET, PATCH | Get details + passport / update |
| `/agents/{id}/kill` | POST | Kill switch |
| `/agents/{id}/reactivate` | POST | Reactivate a suspended agent |
| `/agents/{id}/execute` | POST | Start an execution with a goal |
| `/agents/{id}/executions` | GET | List executions |
| `/agents/{id}/executions/{eid}` | GET | Execution detail + steps |
| `/skills/` | GET | List available skills |
| `/skills/{id}` | GET | Skill details + tools |
| `/policies/` | GET, POST | List / create policies |
| `/policies/{id}` | GET, PATCH, DELETE | Manage a policy |
| `/policies/{id}/rules` | GET, POST | Manage policy rules |
| `/audit-events/` | GET | Paginated, filterable audit log |
| `/costs/` | GET | Aggregated costs, filterable |
| `/costs/summary` | GET | Dashboard summary |
| `/documents/` | GET, POST | RAG document management |
| `/documents/{id}` | GET, DELETE | Manage a document |
| `/documents/{id}/chunks` | GET | Debug: view chunks |
| `/events/stream` | GET | Global SSE stream (all agents) |
| `/events/stream?agent_id={id}` | GET | Per-agent SSE stream |

### 3.3 Communication Interface

Server-Sent Events (SSE), one direction (server → client). Chosen over WebSockets because the client never needs to push real-time data — all mutations are ordinary REST calls, and SSE auto-reconnects via the browser's EventSource API with no extra infrastructure (no Redis pub/sub, no WebSocket upgrade needed).

Event types streamed: `agent_status`, `execution_step`, `policy_decision`, `cost_update`, `kill_switch`, `error`.

### 3.4 Software Interfaces

- **LLM providers**: Groq (primary — fast inference) and Gemini 2.5 Flash (fallback — generous free tier), behind a single `LLMProvider` abstraction. 🔶 EOI deck also lists "Groq/Claude/OpenAI free-tier LLM access" as an option — not reconciled with the Groq+Gemini decision (see §8).
- **Database**: Supabase Postgres (SQLAlchemy 2.0 ORM, Alembic migrations).
- **Auth**: Supabase Auth / GoTrue, issuing JWTs with `user_id`, `role`, `app_metadata.org_id`; validated by FastAPI middleware; RLS policies reference `auth.uid()`/`auth.jwt()` claims directly.

---

## 4. Functional Requirements

Numbered `FR-<module>.<n>`. Full use-case-level detail (actors, flows, business rules, acceptance criteria) lives in `FRD.md` — this section states *what must be true*, not *how it plays out step by step*.

### FR-1 — Authentication & Authorization

- FR-1.1 The system shall authenticate all users via Supabase Auth (JWT-based).
- FR-1.2 The system shall enforce RBAC server-side for every API endpoint (except a health-check endpoint) — `admin` vs `member` at minimum (🔶 see §8 for role-model conflict).
- FR-1.3 The system shall enforce tenant isolation via Postgres Row-Level Security on all tenant-scoped tables, filtering by `organization_id`.

### FR-2 — Agent Management

- FR-2.1 The system shall allow a user to create an agent by providing a name, description, one or more skills, and an owner.
- FR-2.2 Every agent shall have exactly one owner (a user).
- FR-2.3 Every agent shall be assigned a UUID identity and an associated Agent Passport record at creation.
- FR-2.4 The system shall support agent lifecycle states: `DRAFT → COMPLIANCE_CHECK → APPROVED → ACTIVE ⇄ SUSPENDED → REVOKED`.
- FR-2.5 The system shall allow an admin to instantly suspend (kill switch) or reactivate an agent.

### FR-3 — Compliance Check (at agent creation)

- FR-3.1 The system shall run a deterministic (non-LLM) compliance check before an agent can become active, verifying at minimum: the agent has an owner; the agent has at least one skill; the agent's requested permissions are a subset of what its skills require (no over-provisioning); no forbidden permission combination exists.
- FR-3.2 A failed compliance check shall keep the agent in `DRAFT` and log a `compliance_check.failed` audit event with the violation(s).
- FR-3.3 A passed compliance check shall log `compliance_check.passed` and allow the agent to be approved/activated.

### FR-4 — Skill Marketplace

- FR-4.1 The system shall maintain a registry of skills, each declaring: name, display name, description, version, required permissions, trust level, and its tools.
- FR-4.2 Skills shall be registered at application startup by scanning a skills directory; metadata is upserted into the `skills` table (no dynamic upload for MVP).
- FR-4.3 When a user selects a skill for an agent, the agent's Passport shall be populated with the union of all selected skills' required permissions.
- FR-4.4 MVP skills registry shall include at minimum a Ticketing skill, a Document Search (RAG) skill, and a SQL/data-query skill (🔶 aligned to the 3-agent direction — supersedes an earlier "Code Scanner" skill; see §8).

### FR-5 — Policy Engine & Governance Middleware

- FR-5.1 Every tool call issued by the agent runtime shall be intercepted by governance middleware before the underlying tool function executes.
- FR-5.2 The middleware shall deny the call immediately if the agent's Passport `lifecycle_state` is not `ACTIVE`.
- FR-5.3 The middleware shall deny the call if the tool's required permission is not present in the agent's granted permissions.
- FR-5.4 The Policy Engine shall evaluate all enabled policy rules (ordered by priority) against the call context; the first rule that denies wins; if no rule denies, the call is allowed.
- FR-5.5 The system shall support at minimum these policy rule types: `PERMISSION_CHECK` (deny if agent lacks the required permission), `DENY_LIST` (deny specific tool+argument combinations), `RATE_LIMIT` (deny if the agent exceeds N tool calls per minute).
- FR-5.6 If the Policy Engine raises an exception for any reason, the system shall treat this as DENY (fail-closed) — it must never fail open.
- FR-5.7 Every ALLOW or DENY decision shall be logged as an audit event, unconditionally.

### FR-6 — Agent Runtime & Execution

- FR-6.1 The system shall let an authorized user start an execution by supplying a goal to an active agent.
- FR-6.2 The runtime shall reason over the goal, select tools, and loop until the goal is met, a tool call is denied and the LLM cannot proceed, or a maximum step limit is reached.
- FR-6.3 Execution state shall be persisted (checkpointed) so that a crash mid-execution does not lose recorded progress.
- FR-6.4 Execution steps shall be streamed to the frontend in real time via SSE as they occur.
- FR-6.5 If the LLM call fails, the system shall retry with backoff, then fall back to the secondary provider, before failing the execution gracefully; a failed LLM call shall never cause a tool to be re-executed if it already succeeded (idempotency via checkpointed state).
- FR-6.6 On kill switch activation mid-execution, the next governance check (before the next tool call) shall return DENY with a suspension message, and the execution shall terminate gracefully; a hard-cancel fallback shall exist for cases where the graceful path exceeds a timeout.

### FR-7 — The Three Agents

- FR-7.1 **Ticket Manager agent**: shall read a ticket and draft/take an action against it, using the Ticketing skill, subject to the Policy Engine.
- FR-7.2 **RAG agent**: shall retrieve relevant document chunks and answer a question grounded in internal documents, using the Document Search skill; retrieval shall be permission-filtered so the agent cannot retrieve documents outside its granted access scope (pre-filter in the SQL query, not post-filter after vector search).
- FR-7.3 **SQL agent**: shall answer questions over structured data via scoped, **read-only** queries; it shall not be able to execute writes, DDL, or queries outside its permitted schema/tables.

🔶 Both the standalone web-summarizer agent and a standalone cost/budget-analyst agent from the original build spec are **not** part of current scope — see PRD §8/§11.

### FR-8 — Audit Log

- FR-8.1 The system shall create an audit event for every significant action, unconditionally — including: agent created/activated/suspended/revoked/permissions-changed, execution started/completed/failed, tool call allowed/denied/failed, LLM call, kill switch activated, compliance check passed/failed.
- FR-8.2 Audit events shall be immutable and append-only; the application's database role shall not have `UPDATE`/`DELETE` privileges on the audit table.
- FR-8.3 The audit log shall be filterable/paginated (by agent, action, actor, time range) and viewable in the dashboard.

### FR-9 — Cost Tracking (USP)

- FR-9.1 The system shall record a cost event for every LLM call, capturing prompt tokens, completion tokens, total tokens, model, provider, and calculated cost (in USD) from a configurable pricing table.
- FR-9.2 The system shall aggregate cost per agent, per execution, and per model, queryable via the API and visualized on the dashboard.
- FR-9.3 Every agent shall have a configurable budget cap; the Policy Engine shall check remaining budget before allowing a call, alongside the permission check.
- FR-9.4 When an agent's accumulated cost meets or exceeds its budget cap, the system shall automatically transition it to a paused/suspended state and log the reason.
- FR-9.5 Cost figures on the dashboard shall update in real time (via SSE `cost_update` events) as executions run.

### FR-10 — Real-Time Dashboard

- FR-10.1 The dashboard shall show all agents with live status, owner, and running cost.
- FR-10.2 The dashboard shall show a live execution view: steps, tool calls, and policy decisions as they happen, via SSE.
- FR-10.3 The dashboard shall provide a one-click kill switch per agent with immediate effect on any running execution.
- FR-10.4 The dashboard shall provide a cost view: totals and breakdowns by agent/model/time.
- FR-10.5 The dashboard shall provide a policy management view: list policies/rules, toggle enabled/disabled.

---

## 5. Non-Functional Requirements

### 5.1 Security

- NFR-SEC-1 All tool calls are gated by governance middleware; there shall be no code path by which an agent's runtime can invoke a tool function directly, bypassing the middleware.
- NFR-SEC-2 Permissions live in the database, not in LLM context — an agent cannot grant itself permissions via prompt manipulation.
- NFR-SEC-3 RAG retrieval shall be pre-filtered by access scope at the SQL query level (not post-filtered after vector similarity search), so the database never returns unauthorized content.
- NFR-SEC-4 SQL access from the SQL agent shall use a database role restricted to read-only, on a defined table/schema scope, with all queries parameterized (no raw string formatting) and subject to a timeout.
- NFR-SEC-5 Secrets shall never be stored in code or logs; scanned for via `gitleaks` in CI.
- NFR-SEC-6 All tool/RAG output shall be treated as untrusted data by the LLM layer, never as instructions (prompt-injection defense).
- NFR-SEC-7 Fail-closed: any unhandled error in the governance/policy path denies the action by default.
- NFR-SEC-8 🔶 PII redaction before LLM calls is called out in the original project description as a requirement "where applicable," and appears in one architecture-diagram image as a dedicated Presidio-based pipeline stage — not committed to MVP scope; see §8.

### 5.2 Reliability & Failure Handling

| Failure | Required response |
|---|---|
| LLM fails/times out | Retry with backoff → fallback provider → execution fails gracefully |
| External tool/API fails | Tool returns error to the LLM; LLM may retry or report failure |
| Database unavailable | All requests fail closed (503); no tool calls proceed without an audit trail |
| Policy engine fails | DENY (fail-closed) |
| SSE connection drops | Client auto-reconnects; missed events can be fetched via REST |
| Agent process crashes mid-execution | Execution resumes from checkpoint, or is marked `FAILED` |
| Tool execution hangs | 30-second timeout per tool call; timeout surfaces as an error to the LLM |

### 5.3 Performance

- Kill switch propagation: sub-second for the *next* tool call (no interruption of an LLM call already in flight — acceptable per architecture doc for MVP).
- No explicit throughput/latency SLA has been set by the team yet 🔶 — flagged as an open item.

### 5.4 Scalability

- The schema carries `organization_id` on every tenant-scoped table from day one so multi-tenancy is a configuration change later, not a schema migration — but multi-tenant enforcement itself is out of scope for MVP.
- No message broker / external cache is used for MVP (in-process async queue for SSE, in-memory counter for the circuit-breaker) — a deliberate simplicity tradeoff, explicitly documented as something to revisit only if it becomes a bottleneck.

### 5.5 Auditability

- 100% of significant actions produce an audit event, unconditionally (by construction — the middleware logs both ALLOW and DENY paths, and there is no code path that calls a tool without going through the middleware).
- Audit and cost tables are both immutable/append-only at the database privilege level.

### 5.6 Usability

- Dashboard must make "what did this agent do, what was it allowed to do, and what did it cost" answerable at a glance — called out in source material as one of the three things the team must "build exceptionally well" (alongside governance middleware and the audit trail).

### 5.7 Maintainability

- LLM model names and pricing are configuration-driven, never hardcoded.
- All DB access goes through repository classes.
- Domain-centric codebase layout (each domain module owns its models/service/repository; the API layer is a thin HTTP adapter) — intended to keep the codebase navigable for both human and AI-assisted development.

### 5.8 Compliance (as claimed in the EOI submission, not independently verified)

- Least-privilege access via explicit permission scopes.
- Automated pre-activation compliance checklist "inspired by OWASP's guidance on prompt-injection/data-leakage risk."
- Real-time kill switch framed as addressing GDPR/DPDP-style auditability and data-protection expectations.

---

## 6. Data Requirements

### 6.1 Core Entities (summary — see architecture planning doc for full field lists)

| Entity | Purpose | Immutable? |
|---|---|---|
| Organization | Tenant boundary (single org for MVP) | No |
| User | Human user with a role | No |
| Agent | An AI agent registered in the system | No |
| AgentPassport | Identity, permissions, compliance status, lifecycle state | No (changes audited) |
| Permission | A scoped capability granted to an agent (`resource:action`) | No (changes audited) |
| Skill | Reusable capability bundle | Metadata mutable; code immutable per version |
| Tool | A single callable function within a skill | Same as Skill |
| Policy / PolicyRule | Named governance rule set / individual rule | No |
| Execution / ExecutionStep | One agent run / one reasoning+tool-call cycle within it | Status mutable; history append-only |
| PolicyDecision | The allow/deny result of a governance check | **Yes — immutable** |
| AuditEvent | A structured log entry | **Yes — immutable, append-only** |
| CostEvent | Token usage + cost for one LLM/tool call | **Yes — immutable** |
| Document / DocumentChunk | An ingested document for RAG / its embedded chunks | Metadata mutable / replaced on re-ingestion |

### 6.2 Storage

PostgreSQL (Supabase) for all relational data; pgvector extension for document chunk embeddings. No separate log store — audit/cost data lives in regular Postgres tables, which the team judged sufficient for demo-scale volume (thousands to low millions of events).

### 6.3 Data Types Supported

- PDF / docs / tickets / unstructured text → RAG pipeline (chunk + embed + retrieve)
- Excel / CSV / SQL → scoped, read-only query tool (not naive embedding — structured data needs computation)
- JSON → schema-validated ingestion

---

## 7. Other Requirements

### 7.1 Deployment

Vercel (frontend) + Railway (backend) + Supabase (database). Migrations via Alembic, run as part of deployment, before backend deploy, before frontend deploy.

### 7.2 CI/CD

GitHub Actions: on PR — install, lint (ruff/eslint), type-check (pyright/tsc --strict), unit tests (pytest/vitest), `gitleaks` scan, build. On merge to main — all PR checks + integration tests against a shared Supabase test project + deploy backend + run migrations + deploy frontend.

### 7.3 Testing Strategy

Testing pyramid: unit tests (domain logic, cost calculation, permission checks) → API/integration tests (policy engine, governance middleware, agent lifecycle) → 2–3 critical E2E paths (Playwright: agent creation → execution → audit). Non-regression scenarios explicitly called out as must-never-break: authorized call → ALLOW, unauthorized call → DENY, suspended agent → all calls DENY, revoked agent → cannot execute, RAG respects access scope, kill switch stops a running agent, a cost event is created for every LLM call, an audit event is created for every tool call.

### 7.4 Monitoring

Sentry (application errors, free tier) + structured JSON logs (`structlog`) to stdout. No external metrics infrastructure for MVP — dashboard metrics are computed directly from Postgres tables.

---

## 8. Open Questions (consolidated from source-material conflicts)

See PRD.md §11 for the full table. Summary of items that materially affect this SRS if resolved differently:

1. **Orchestration framework** — LangGraph vs. CrewAI (both appear as if decided, in different documents).
2. **Vector database** — Supabase pgvector (decided, with rationale, in the main architecture doc) vs. Chroma (EOI deck).
3. **Auth provider** — Supabase Auth (decided, with rationale) vs. Clerk (appears in a stale diagram).
4. **Role model** — `admin`/`member` (architecture doc) vs. `owner`/`builder`/`auditor`/`admin` (original project description).
5. **Agent roster** — 3 agents (current direction: Ticket Manager, RAG, SQL) vs. 4+ agents (original spec, including a standalone cost/budget-analyst agent).
6. **Guardrails/observability depth** — Sentry+structlog (documented, decided) vs. Presidio/NeMo Guardrails/Cohere Rerank/Arize Phoenix (appears in one diagram image only, not written into any decided spec).
7. **RAG sophistication** — simple fixed-size chunking (documented) vs. hybrid search + reranking + CRAG self-correction (diagram image only).
8. **SQL agent safety mechanism** — not specified in prose anywhere except "read-only"; `sqlglot` AST validation appears only in a diagram image.
9. **LLM provider set** — Groq+Gemini (architecture doc, decided) vs. "Groq/Claude/OpenAI" (EOI deck, looser framing).
10. **Performance SLAs** — none defined yet.

None of these block writing this SRS, but all of them should be resolved (or explicitly deferred with a written rationale) before implementation begins on the affected module.
