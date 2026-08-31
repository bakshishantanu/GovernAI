<!--
Sync Impact Report
- Version change: TEMPLATE (unratified) → 1.0.0
- Rationale: Initial ratification. The prior file was an unfilled scaffold (all
  placeholder tokens); this is the first concrete constitution, not an amendment.
- Modified principles: N/A (no prior ratified principles existed)
- Added principles:
  1. Governance-Gated Execution
  2. Least-Privilege Resource Access
  3. Explicit Skill Schemas
  4. Declared Skill Permissions
  5. Fail-Closed by Default
  6. Orchestrator Cannot Bypass Policy
  7. Credential Isolation
- Added sections: Technology & Scope Constraints, Development Workflow, Governance
- Removed sections: none
- Templates reviewed for consistency: plan-template.md, spec-template.md,
  tasks-template.md, checklist-template.md — all reference "the constitution"
  generically with no hardcoded principle text, so no follow-up edits are
  required there. Re-check them if a future amendment renames or removes a
  principle referenced by name in generated artifacts.
- Deferred TODOs: none
-->

# GovernAI Constitution

## Core Principles

### 1. Governance-Gated Execution
Every agent execution MUST pass through the governance layer before any tool call
executes. There MUST NOT be a code path by which an agent's runtime can invoke a
tool function directly, bypassing this layer — no exceptions for "trusted" tools,
internal tools, or read-only tools.
Rationale: governance that can be routed around is not governance. The moment one
tool call bypasses the check, the platform's core guarantee — every action is
scoped and audited — is void.

### 2. Least-Privilege Resource Access
Agents MUST NOT access any resource, tool, or data outside the permissions
explicitly declared on their Agent Passport. A request for out-of-scope access
MUST be denied outright, never silently narrowed, approximated, or partially
served.
Rationale: permissions exist to bound what an agent can do. Partial or "best
effort" enforcement is equivalent to no enforcement.

### 3. Explicit Skill Schemas
Every skill's tools MUST declare a formal input schema (parameters, with types)
and a predictable output shape. Implicit, undocumented, or free-form parameters
are not permitted.
Rationale: a schema is what makes a tool call validated before it executes, and
predictable output is what keeps downstream governance and audit logging
meaningful rather than best-effort.

### 4. Declared Skill Permissions
Every skill MUST declare the exact permissions its tools require. An agent's
granted permission set MUST be derived only from the union of its bound skills'
declared permissions — manual over-provisioning of an agent beyond what its
skills require is not permitted.
Rationale: this is what makes the pre-activation compliance check meaningful —
if permissions could be granted independent of skills, the check would be
theater, not enforcement.

### 5. Fail-Closed by Default
Any unauthorized, ambiguous, or errored authorization decision MUST resolve to
DENY. The system MUST NOT fail open under any circumstance — including policy
engine exceptions, database unavailability, malformed input, or unexpected
internal errors.
Rationale: an availability failure that quietly becomes a security failure is
unacceptable in a governance platform whose entire purpose is safety guarantees.

### 6. Orchestrator Cannot Bypass Policy
The orchestrator (agent runtime, LangGraph or equivalent) MAY decide which skill
or tool to invoke, but MUST NOT invoke it directly. Every invocation, regardless
of which component selected it, MUST pass through the same governance/policy
enforcement path as any other call. No component is a "trusted caller" exempt
from Principle 1.
Rationale: skill selection is a reasoning decision; permission to act is a
security decision. Conflating the two would let the orchestrator become a de
facto bypass of the entire governance layer.

### 7. Credential Isolation
Sensitive credentials (API keys, database credentials, tokens) MUST NOT be
exposed to agents or included in any LLM-visible context — not in prompts, tool
arguments, or tool outputs. Credentials are used only by the adapter/provider
code that calls the underlying system; agent reasoning never sees them.
Rationale: an LLM's context is not a trust boundary. Prompt injection or
tool-output manipulation must not be able to exfiltrate a secret that was never
placed within reach in the first place.

## Technology & Scope Constraints

GovernAI's MVP is single-organization only; the schema carries `organization_id`
on every tenant-scoped table so multi-tenancy is a future configuration change,
not a schema migration, but multi-tenant enforcement itself is out of scope for
MVP. All external integrations (ticketing, document search, structured data)
MUST use mock adapters behind a real adapter interface for MVP — no live
third-party integrations. LLM and embedding usage MUST stay within free-tier-
compatible providers; model names and pricing are always configuration, never
hardcoded, since provider lineups and rates change frequently. All database
access MUST go through repository classes — no raw SQL in service or business
logic.

## Development Workflow

Work happens on feature branches named `<owner>/<short-description>` (matching
each person's CODEOWNERS role) — never committed directly to `main`. Every
change is proposed via Pull Request; CODEOWNERS-designated owners are notified
for the areas a PR touches. Any change to the governance middleware, policy
engine, or agent runtime MUST keep the non-regression scenarios in SRS §7.3
passing: authorized call → ALLOW, unauthorized call → DENY, suspended agent →
all calls DENY, revoked agent → cannot execute, RAG retrieval respects access
scope, kill switch stops a running execution, a cost event exists for every LLM
call, an audit event exists for every tool call. New code ships with automated
tests; a feature is not considered done until its tests pass locally.

## Governance

This constitution supersedes ad hoc practice. Where it conflicts with an
unreconciled 🔶-flagged item in FRD.md/PRD.md/SRS.md, this constitution's
principles take precedence for anything touching governance, permissions, or
security, until the team explicitly amends this document. Amendments require a
Pull Request that updates this file, states the version bump and rationale in
its description, and is merged through the same review process as any other
change. Any PR touching the governance middleware, policy engine, or agent
runtime MUST state in its description which Core Principles it upholds.

**Version**: 1.0.0 | **Ratified**: 2026-08-31 | **Last Amended**: 2026-08-31
