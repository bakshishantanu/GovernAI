# Implementation Plan: SQL Query Skill

**Branch**: `001-sql-query-safety` | **Date**: 2026-08-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-sql-query-safety/spec.md`

## Summary

A new skill (`SqlQuerySkill`, one `run_sql_query` tool) that lets an agent answer
computation/aggregation questions over structured data. The LLM generates a candidate SQL
query directly; that query is treated as fully untrusted and must pass AST-based validation
(read-only, no DDL, tables within the agent's fine-grained per-table permissions) before it
ever reaches the database, which itself is also opened as a read-only connection as a second,
independent layer of protection. MVP storage is a small seeded SQLite dataset behind an
adapter interface, matching how the existing Ticketing skill's mock adapter is structured, so
a real read-only Postgres role can replace it later without changing the tool's interface.

## Technical Context

**Language/Version**: Python 3.13 (matches `backend/pyproject.toml`, `requires-python = ">=3.12"`)

**Primary Dependencies**: `app.skills.base` (existing `BaseSkill`/`BaseTool` ABCs), `sqlglot`
(new — AST-based SQL parsing for validation), Python's built-in `sqlite3` (MVP mock dataset)

**Storage**: SQLite, file-based, seeded with a small mock dataset — matches FRD-04's rule that
all MVP skills use mock adapters behind a swappable interface

**Testing**: `pytest` + `pytest-asyncio` (existing pattern, see `backend/tests/skills/`)

**Target Platform**: Backend service module (Python), same runtime as the rest of `backend/`

**Project Type**: Addition to the existing single-service Python backend — not a new project

**Performance Goals**: No project-wide SLA exists yet (SRS §5.3). This feature's only explicit
performance requirement is FR-005's execution timeout (proposed default: 10s, config-driven,
not hardcoded — consistent with SRS §2.7 on config-driven behavior).

**Constraints**: Query execution MUST use a connection with no write privileges (FR-004);
validation MUST complete fully before execution (FR-002/003/010) with zero tolerance — a
validator error or ambiguity MUST resolve to denial, never to "allow because unsure" (ties to
Constitution Principle 5, Fail-Closed by Default).

**Scale/Scope**: MVP demo scale — a handful of seeded tables/rows, consistent with the existing
Ticketing skill's ~3 seeded records.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|---|---|---|
| 1 | Governance-Gated Execution | PASS | This feature only adds a `BaseTool`; every call still goes through the same governance middleware wrap as any other tool (P1's runtime concern, unchanged by this feature). No trusted shortcut is introduced. |
| 2 | Least-Privilege Resource Access | PASS | Directly implemented by FR-003/FR-011 — fine-grained per-table permissions, denial (not partial execution) on any out-of-scope reference. |
| 3 | Explicit Skill Schemas | PASS | The tool declares a JSON-schema `parameters` field, same as every existing `BaseTool` (Contract 5). |
| 4 | Declared Skill Permissions | PASS | Per-table permissions (`sql:read:<table>`) are declared per skill instance/configuration, consistent with `required_permissions` on `BaseSkill`. |
| 5 | Fail-Closed by Default | PASS | FR-002/003/005/010 all resolve to denial on any write attempt, out-of-scope reference, timeout, or parse failure — never a silent allow. |
| 6 | Orchestrator Cannot Bypass Policy | PASS | No orchestrator-level change in this feature; the tool has no alternate invocation path outside normal governance-wrapped tool calls. |
| 7 | Credential Isolation | PASS | The database connection/credentials live only in the adapter's constructor, never in tool arguments, tool output, or LLM-visible context. |

No violations. Complexity Tracking table is omitted (nothing to justify).

**Post-Design Re-check** (after Phase 1 — data-model.md, contracts/, quickstart.md): all 7
principles still PASS. Confirmed concretely rather than just asserted: `data-model.md`'s
`QueryValidationResult` defaults to `allowed = False` on any parse failure (Principle 5);
`contracts/run_sql_query_tool.md` explicitly excludes credentials and raw driver exceptions
from every output shape (Principle 7); permission scoping in `data-model.md` uses per-table
`sql:read:<table>` strings, not a single blanket permission (Principle 2). No new violations
introduced by the design.

## Project Structure

### Documentation (this feature)

```text
specs/001-sql-query-safety/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/             # Phase 1 output
└── tasks.md               # Phase 2 output (/speckit-tasks - not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── skills/
│   │   ├── base.py                 # existing - BaseSkill/BaseTool ABCs (unchanged)
│   │   ├── ticketing.py            # existing - reference pattern (unchanged)
│   │   └── sql_query.py            # NEW - SqlQuerySkill, RunSqlQueryTool
│   └── runtime/
│       └── sql/
│           ├── __init__.py         # NEW
│           ├── validator.py        # NEW - AST-based validation (sqlglot): read-only + scope check
│           └── adapter.py          # NEW - SqlDataAdapter: seeded SQLite + read-only execution + timeout
└── tests/
    ├── skills/
    │   └── test_sql_query.py       # NEW
    └── runtime/
        └── sql/
            ├── test_validator.py   # NEW
            └── test_adapter.py     # NEW
```

**Structure Decision**: This is an addition to the existing single-service Python backend
(`backend/app/`), not a new project or a "web application" split — the frontend/backend split
already exists project-wide and this feature only touches the backend. Query validation and
data access are split into their own `runtime/sql/` subpackage (mirroring the existing
`runtime/llm/` pattern of `base.py`/provider-specific files/`service.py`) rather than being
inlined into the skill file, because both the validator and the adapter are substantial enough
to need independent unit tests and are conceptually reusable beyond just this one skill.

## Complexity Tracking

*No violations — table omitted.*
