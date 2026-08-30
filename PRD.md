# GovernAI — Product Requirements Document (PRD)

## Document Control

| Field | Value |
|---|---|
| Project | GovernAI |
| Tagline | "Build Agents Fast. Govern Them Faster." |
| Program | Deloitte Capstone Program 2026 |
| Institution | Manipal University Jaipur |
| Team | Fennec |
| Participants | Pranav Ladha (pranavladha612@gmail.com), Priya Agrawal (priyaagr7000@gmail.com), Shantanu Bakshi (bakshi.shantanu05@gmail.com) |
| Status | **DRAFT — NOTHING IN THIS DOCUMENT IS FINALIZED** |
| Version | 0.1 |
| Date | 2026-08-19 |
| Sources | Deloitte EOI response deck, internal architecture planning notes (50-page working doc), whiteboard/diagram photos, team chat discussion |

> **How to read this document**: This PRD consolidates everything the team has discussed and written so far into one place, *before* any build work starts. Several source materials disagree with each other on specific technical choices (see §11, Open Questions). Nothing here should be treated as locked until the team explicitly signs off on it. Where the team's most recent direction (this conversation, 2026-08-19) overrides an older document, that is called out explicitly.

---

## 1. Purpose

GovernAI is a platform for **building and governing internal AI agents**. Instead of coding an agent from scratch, builders assemble it from reusable, pre-built "skills." The moment an agent is created, it automatically receives an identity, a scoped permission set, and a live cost budget — governance is generated at creation time, not configured afterward.

This document defines *what* GovernAI needs to do and *why*, for the Deloitte Capstone 2026 submission and prototype build. It is the business/product-level counterpart to the SRS (system-level requirements) and FRD (feature-level functional specs).

---

## 2. Problem Statement

Enterprises deploying AI agents today have effectively no governance layer:

- Teams build agents in isolation, duplicating integrations/connectors that already exist elsewhere in the org.
- Agents get unmonitored access to internal data with no consistent identity or permission model.
- Nobody can answer basic questions leadership will ask: *"How much are we spending on agents?"* or *"Can we pause this one right now?"*

**Left unsolved**, this creates compliance risk (ungoverned data access), budget overruns (untracked LLM/API spend), and wasted engineering effort (the same connector rebuilt by every team).

---

## 3. Goals, Objectives & KPIs

**Goal**: Make agent-building fast *and* safe by assembling agents from ready-made "skills" (ticketing connector, doc search, SQL query tool, etc.), with identity, permission scope, and an audit trail built in automatically — not bolted on later.

**KPIs** (as proposed to Deloitte; not yet instrumented):
- % reduction in build time per new agent (via skill reuse vs. building from scratch)
- % of agent actions covered by the audit log (target: 100%, by construction — logging is unconditional)
- Live, real-time cost-per-agent visibility for leadership (binary: available or not, then accuracy of the figure)

---

## 4. Target Users / Personas

| Persona | Needs GovernAI for |
|---|---|
| **Platform / security engineers** | Install GovernAI as the mandatory checkpoint every new agent must pass through before it can act. |
| **Agent builders** | Assemble agents from existing skills instead of writing integrations from scratch. |
| **IT / security leadership & budget owners** | Dashboard view of every agent — owner, access, cost — with the ability to pause any agent instantly. |

---

## 5. Product Overview

GovernAI is composed of six conceptual modules:

1. **Dashboard** (Next.js) — live view of every agent: status, actions, cost, kill switch.
2. **API / Backend** (FastAPI) — auth, business logic, DB access, REST/SSE endpoints.
3. **Skill Marketplace** — catalog of reusable connectors (ticketing, document search/RAG, SQL query tool, etc.), each declaring the permissions it requires.
4. **Agent Definition Layer** — the custom logic per agent (a graph defining which skills it calls, in what order, with what prompts/rules). This is where per-agent customization happens, on top of shared skills.
5. **Agent Runtime** — executes whatever the Agent Definition Layer defines.
6. **Passport / Policy Engine** — per-agent identity, permission scope, and cost budget. Intercepts every tool call live; allowed or blocked, the outcome and its cost are always logged.

**Skill vs. agent**: a skill is a reusable tool (shared library); an agent is custom logic built on shared skills (an app using that library). Two agents that both need RAG import the same RAG skill but have distinct logic around it.

### Data flow (conceptual)

```
User request → Agent Runtime selects a skill (per its own graph)
  → Policy Gate checks: permission scope AND cost budget
      → both pass → call reaches the real system (ticketing/docs/DB)
      → either fails → blocked
  → EVERY call (allowed or blocked) + its cost → Audit Log (append-only, unconditional)
  → Dashboard reads from the log: live status, cost per agent, kill switch
```

---

## 6. Headline USP & Differentiators

**Headline USP — Live cost/FinOps governance**: every agent gets a real-time spending budget that auto-pauses it if exceeded. Most competing "agent governance" platforms (Microsoft Agent 365, Okta, Willow, Credo AI, IBM watsonx.governance) treat cost as secondary to identity/security governance. GovernAI makes cost control the primary, demoable feature. **This is confirmed as the project's USP.**

**Secondary differentiator**: identity + scope + budget are generated automatically at agent creation, not configured separately afterward — most competitors are governance-only tools that don't help *build* the agent.

**Additional angle (from EOI submission)**: agents "arrive pre-governed" — an automated compliance check runs at creation and blocks activation if it fails, rather than governance being an afterthought bolted onto a running agent.

---

## 7. Scope

### 7.1 In scope for MVP (Deloitte demo)

| Capability | MVP Scope |
|---|---|
| Agent creation | Form-based: name, description, select skills, assign owner |
| Agent identity | UUID, human-readable name, Agent Passport record |
| Agent ownership | Every agent has exactly one owner (a user) |
| Permission scoping | RBAC with scoped permission sets per agent (e.g. `ticket:read`, `docs:search`) |
| Skill selection | Pick from a curated registry of skills (see §8) |
| Policy enforcement | Governance middleware intercepts every tool call; evaluated against the agent's permission set + global deny rules |
| Tool execution | Agent runtime invokes tools only after the governance check passes |
| Audit logging | Append-only log captures every significant action (allowed + blocked) |
| Cost tracking | Token counts + model pricing → per-agent, per-execution cost attribution, with a visible enforced budget cap |
| Dashboard monitoring | Real-time agent list, status, recent actions, cost breakdown |
| Agent blocking / kill switch | One-click suspend from the dashboard, immediate effect on running executions |

### 7.2 Explicitly out of scope for MVP

- Multi-organization / multi-tenant (single-org only; data model is tenant-*ready*, not tenant-*active*)
- Skill marketplace UI for uploading community-built skills
- Skill versioning beyond v1
- Fine-grained ABAC policies (data-driven rule DSL)
- Real OAuth integrations with live external systems (Zendesk/GitHub/etc.) — MVP uses mock adapters behind a real adapter interface
- Email skill
- Agent-to-agent communication
- Billing / payment
- Mobile UI

### 7.3 Must-have vs. optional (per the original 4-week build framing)

**Must-have**: one agent fully working end-to-end with real tool calls; Passport blocking a real action live; per-agent cost tracking with a visible, enforced budget cap; append-only audit log; dashboard; kill switch.

**Optional if time allows**: all agents live simultaneously and visibly reusing shared skills; hash-chained audit log; tiered LLM routing fully implemented.

---

## 8. The Agents (current direction)

> ⚠️ **This supersedes earlier drafts.** The original architecture write-up proposed four demo agents (RAG knowledge agent, Ticket action taker, Web summarizer/researcher, Cost/budget-analyst agent) plus optional 5th/6th agents (SQL analyst, PII redaction). **As of this conversation, the team has narrowed scope to three agents**, and cost tracking is *not* a standalone agent — it is a platform-level capability (Policy Engine + Cost dashboard) that governs all three agents.

| # | Agent | Purpose |
|---|---|---|
| 1 | **Ticket Manager agent** | Reads a ticket, drafts/takes an action against it. Doubles as the live governance/policy-gate demo (a manual-approval vs. fully-automated toggle was discussed as a stretch feature — see Open Questions). |
| 2 | **RAG agent** | Retrieves and answers from internal documents (chunk + embed + retrieve pipeline). |
| 3 | **SQL agent** | Scoped, read-only query tool over structured data (Excel/CSV/SQL) — numbers need computation, not naive text-chunking/embedding. |

**Not currently in scope** (explicitly per this conversation): a standalone web summarizer/researcher agent, and a standalone cost/budget-analyst agent. Cost visibility is delivered instead via the platform's own dashboard and audit log, which is consistent with the USP being a *platform* capability rather than a 4th agent.

---

## 9. Success Metrics (demo-level)

- One agent runs a full task end-to-end using real (mock-adapter) tool calls.
- A live demo shows one agent's tool call being **blocked** by the Policy Engine in real time.
- A live demo shows an agent's cost climbing on the dashboard and **auto-pausing** when it crosses its budget.
- Audit log shows a complete, unconditional record (allowed + blocked + cost) for a full execution.
- Kill switch demonstrably stops a running agent within one tool-call cycle.

---

## 10. Assumptions

(From the EOI submission — not re-validated by the team since.)

- The enterprise already has basic cloud/API access and sanctioned data sources.
- Agents operate only through approved connectors (skills) — no raw, unmonitored system access.
- Users have defined roles/teams for permission-scoping.
- Prototype runs entirely on free-tier services (near-zero build cost).

---

## 11. Open Questions / Unresolved Decisions

The source materials the team supplied disagree with each other on several points. None of these are resolved by this PRD — they need an explicit team decision.

| Topic | Option A (source) | Option B (source) | Status |
|---|---|---|---|
| Orchestration framework | LangGraph (architecture planning doc, tech stack table, diagram images — treated as decided there) | CrewAI mentioned as an equal alternative (EOI deck, twice) | **Open** — architecture doc leans LangGraph but EOI still lists both |
| Vector DB | Supabase Postgres + pgvector (architecture doc, decided with rationale vs. Neon) | Chroma (EOI deck "Proposed Tech Stack" and "Competency/Tools" sections) | **Open** — these two docs directly conflict |
| Auth provider | Supabase Auth / GoTrue (architecture doc §15, explicitly decided over Clerk, with rationale) | Clerk (appears in an architecture *sequence diagram* image and in an earlier tech-stack table image) | **Likely resolved toward Supabase Auth**, but diagrams weren't updated to match — needs a pass to fix stale diagrams |
| Agent roster | 4 agents: RAG, Ticket action taker, Web summarizer, Cost/budget analyst (+ optional SQL, optional PII) — original build spec | 3 agents: Ticket Manager, RAG, SQL — this conversation, 2026-08-19 | **This PRD follows the 3-agent direction** per explicit latest instruction |
| Guardrails/observability stack | Microsoft Presidio (PII), NeMo Guardrails (Colang 2.0), Cohere Rerank or bge-reranker, Arize Phoenix (observability) — appears in one architecture-diagram photo only | Sentry + structlog (main architecture doc, tech stack table, and original project description) | **Open** — the Presidio/NeMo/Cohere/Phoenix stack looks like a stretch/aspirational sketch, not reflected anywhere else. Needs a decision on whether any of it is in scope given free-tier/time constraints. |
| Team size | 3 named participants (EOI slide 2) | "Team of 3" (EOI slide 4) vs. "4-person team" (EOI slide 7, cost/effort section) | **Inconsistency in the EOI deck itself** — flagging for correction before submission, not a product decision |
| Ticket agent approval mode | Manual-approval vs. fully-automated toggle, described as doubling as a HITL/policy-gate demo | Not mentioned in the architecture planning doc's agent/phase breakdown | **Open** — nice-to-have, not committed |
| RAG chunking/retrieval sophistication | Simple fixed-size chunking (~512 tokens, 50-token overlap), single embedding model — main architecture doc | Hybrid pgvector + tsvector FTS with RRF fusion, contextual chunk prepending, CRAG self-correction loop, reranker — one diagram image only | **Open** — the diagram version is materially more complex than the written plan; needs a scope decision |
| SQL agent safety | Not detailed anywhere except "scoped read-only query/code tool" in the original project description | sqlglot AST validation + read-only DB role + timeouts — one diagram image only | **Open** — the diagram's approach is a reasonable default but hasn't been written into any spec text |

**Recommendation for resolving these**: treat the main 50-page architecture planning doc as the primary source of truth for anything it explicitly decided (it says so itself: "All architectural decisions are finalized" — though per your instruction we are *not* treating that claim as binding), and treat the single diagram-photo items (Presidio/NeMo/Cohere/Phoenix, hybrid RAG, sqlglot) as a separate "stretch architecture" track to be consciously accepted or dropped, not silently merged in.

---

## 12. Risks

| Risk | Mitigation (as proposed) |
|---|---|
| Orchestration framework learning curve (LangGraph) could delay the whole runtime phase | Start with the simplest possible graph (single agent, no branching); keep a fallback plan to use a simpler tool-calling loop |
| Free-tier LLM reliability (Groq / Gemini) — rate limits or downtime during the live demo | Circuit-breaker + fallback provider; pre-cache demo scenarios; consider a small paid Groq plan as insurance |
| Time pressure — tight timeline for a small team | Phases prioritized by demo value; lower-priority phases (e.g. RAG polish, hardening) are the first to be descoped if time runs short |
| Scope disagreement across source docs (see §11) | Resolve explicitly before Week 1 build starts, rather than letting each teammate build against a different version |

---

## 13. Timeline / Milestones

Two versions of the timeline exist in the source material and have not been reconciled — both are shown for reference; neither is treated as final.

**EOI deck version (3 checkpoints, 6 weeks, team of 3):**
1. **Checkpoint 1 (Wk 1–2)**: one agent runs a full task end-to-end (read ticket → search docs → draft reply) — proves the core engine.
2. **Checkpoint 2 (Wk 3–4)**: that agent has an owner, scoped permissions, a live action log; one hard-coded blocking rule demoed live.
3. **Checkpoint 3 (Wk 5–6)**: a second, independent agent is stood up reusing the first agent's building blocks; both visible on one dashboard; demo rehearsed.

**Architecture planning doc version (8 phases, ~20–28 days, within a 5–6 week window):**
Phase 0 Foundation → Phase 1 Agent Runtime → Phase 2 Governance Layer → Phase 3 Skills & Marketplace → Phase 4 Audit/Cost/Real-time → Phase 5 RAG Pipeline → Phase 6 Dashboard & Kill Switch → Phase 7 Security Hardening & Polish.

Both agree on the same underlying shape (runtime first, governance second, breadth/polish last) — the discrepancy is granularity, not direction.

---

## 14. Competitive Landscape (brief)

Microsoft Agent 365, Okta, Willow, Credo AI, IBM watsonx.governance — all focus primarily on identity/security governance and treat cost as secondary. GovernAI's stated bet is that leading with live, enforced cost governance is the differentiated, demoable feature, while still covering identity/scope as table stakes.

---

## 15. Feasibility & Cost (from EOI submission)

- **Technical feasibility**: built on proven open-source orchestration — governance is layered on existing tech, not new AI research.
- **Economic feasibility**: entire prototype targeted at free-tier services end-to-end; near-zero cost to build.
- **Operational feasibility**: integrates via standard APIs/webhooks (Zendesk, GitHub, internal DBs) — sits alongside existing systems, doesn't replace them.
- **Effort estimate (EOI)**: ~120–150 hours, over 5–6 weeks. (Team size stated inconsistently as 3 vs. 4 — see §11.)
- **ROI framing**: engineering hours saved per new agent via skill reuse, plus avoided cost of compliance incidents caught early.
