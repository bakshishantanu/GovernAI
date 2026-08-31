# Research: SQL Query Skill

All Technical Context fields were resolved directly (no open `NEEDS CLARIFICATION` markers),
using the three answers already given during `/speckit-specify` clarification. This document
records the *why* behind each resulting technical decision.

## Decision: SQL parsing library — `sqlglot`

**Decision**: Use `sqlglot` to parse each LLM-generated candidate query into an AST before
execution.

**Rationale**: The user's clarification answer (Q2) explicitly requires full AST-based
validation over keyword/pattern matching, specifically because keyword checks are bypassable
(e.g. a write statement hidden inside a comment-stripped or re-cased string, or a second
statement smuggled in after a semicolon). `sqlglot` is a mature, actively maintained, pure-Python
SQL parser/transpiler with no external service dependency (fits the project's free-tier/
no-extra-infra constraint) and exposes exactly what's needed here: parse to an AST, walk it to
find statement type (SELECT vs. INSERT/UPDATE/DELETE/DDL) and every table reference.

**Alternatives considered**:
- **Regex/keyword blocklist** (e.g. reject strings containing `INSERT`, `DROP`, ...) — rejected
  per the user's explicit Q2 answer; also trivially bypassable (e.g. a column literally named
  `insert_date` would false-positive, while a disguised statement could false-negative).
- **`sqlparse`** (older, more permissive tokenizer, not a full AST) — rejected because it
  tokenizes rather than producing a structured tree, making "does this reference table X"
  harder to answer reliably than with `sqlglot`'s AST traversal.
- **A restricted query DSL instead of raw SQL** — rejected because it would have contradicted
  the user's explicit Q1 answer (LLM generates real SQL text, not a constrained DSL).

## Decision: MVP data storage — seeded SQLite, opened read-only for execution

**Decision**: Use Python's built-in `sqlite3` for the MVP mock dataset. The *validation* path
uses a normal connection to introspect schema for permission checks; the *execution* path opens
a second connection with SQLite's read-only URI mode (`file:...?mode=ro`) as an independent,
connection-level enforcement layer beneath the AST validation.

**Rationale**: FRD-04's business rule requires all MVP skills to use mock/seeded adapters behind
a real interface, matching the existing `TicketingSkill`/`TicketingAdapter` pattern. SQLite
needs no external service (keeps the free-tier/near-zero-infra constraint from PRD §10), yet
unlike the Ticketing skill's plain Python objects, it is *actually* a real SQL engine — so the
same query-validation code path exercised here will keep working unchanged when a real
Postgres read-only role replaces this adapter later (NFR-SEC-4), only the adapter's connection
target changes.

**Alternatives considered**:
- **Plain Python dicts/lists** (like `TicketingAdapter`) — rejected because the whole point of
  this feature is validating and executing *real SQL*; a fake in-memory query engine would not
  exercise the actual validation/execution path this feature exists to prove out.
- **A real Postgres instance for MVP** — rejected as unnecessary infrastructure for MVP; the
  adapter interface is designed so this swap-in happens later without touching the skill or
  validator code (mirrors NFR-SEC-4's requirement directly).

## Decision: Permission naming — `sql:read:<table_name>`

**Decision**: One permission string per permitted table, formatted `sql:read:<table_name>`,
granted to an agent's Passport the same way `ticket:read`/`docs:search` already are.

**Rationale**: The user's Q3 answer requires fine-grained per-table scoping. This format is a
direct extension of the platform's existing `resource:action` permission convention (FRD-01/
FRD-04), so no new permission model needs to be introduced — the compliance check, Passport
storage, and audit logging all already understand this shape.

**Alternatives considered**:
- **A single `sql:read` permission covering all tables in a skill instance** — rejected; this
  is exactly the "one fixed dataset per skill instance" option the user explicitly rejected
  in Q3.
- **Table permissions as a separate list field on the skill rather than the permission set** —
  rejected because it would need its own enforcement path outside the existing Passport/
  permission-check machinery, duplicating logic Principle 2 (Least-Privilege) already covers.

## Decision: Timeout enforcement

**Decision**: A per-query timeout (default 10s), read from configuration (never hardcoded, per
SRS §2.7 and this project's existing pattern for the LLM pricing table).

**Rationale**: FR-005 requires a timeout; no project-wide performance SLA exists yet (SRS §5.3)
to derive a more specific number from, so 10s is a reasonable MVP default consistent with the
30s tool-call timeout already used elsewhere in the platform (FRD-06), while being tighter since
a runaway read query has no legitimate reason to approach that ceiling.

**Alternatives considered**:
- **Reusing the platform-wide 30s tool-call timeout as-is** — rejected as too loose for a
  single SQL query specifically (30s is sized for a whole tool call including any external
  latency, not one local query).
