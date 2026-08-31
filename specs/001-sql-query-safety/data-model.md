# Data Model: SQL Query Skill

## ScopedQueryRequest

The input to the validation+execution pipeline for one tool call.

| Field | Type | Notes |
|---|---|---|
| `question` | str | The natural-language question the LLM was asked to answer |
| `candidate_sql` | str | The raw SQL text the LLM generated in response — always untrusted (FR-009) |
| `permitted_tables` | set[str] | The calling agent's permitted table names, derived from its `sql:read:<table>` permissions (FR-011) |

## QueryValidationResult

The outcome of validating a `ScopedQueryRequest` before any execution is attempted. Immutable
once produced.

| Field | Type | Notes |
|---|---|---|
| `allowed` | bool | `False` on any write/DDL statement, any out-of-scope table reference, or any parse failure (fail-closed per Constitution Principle 5) |
| `reason` | str \| None | Human-readable denial reason when `allowed` is `False`; `None` when allowed |
| `referenced_tables` | list[str] | Every table the parsed query references, used both for the scope check and for audit logging |
| `statement_type` | str | e.g. `SELECT`, `INSERT`, `DROP` — the AST-derived statement kind, always recorded even on denial |

**Validation rules** (from FR-002, FR-003, FR-010):
- `statement_type` MUST be `SELECT` (or another explicitly read-only form) — anything else →
  `allowed = False`.
- Every entry in `referenced_tables` MUST be a subset of `permitted_tables` — any table not in
  that set → `allowed = False`, including when only one table in a JOIN is out of scope.
- A `candidate_sql` that fails to parse at all → `allowed = False` (never treated as "unknown,
  so allow").

## QueryResultSet

The successful, executed result of a permitted query.

| Field | Type | Notes |
|---|---|---|
| `columns` | list[str] | Column names, in result order |
| `rows` | list[dict] | Each row as a `{column: value}` mapping |
| `row_count` | int | `len(rows)` — `0` is a valid, successful result (FR-008), not an error |

## SqlDataAdapter (mock, MVP)

Not a request/response entity, but the storage-facing component referenced throughout the plan.

| Responsibility | Notes |
|---|---|
| Holds the seeded SQLite dataset | Mirrors `TicketingAdapter`'s role: mock data behind a swappable interface |
| Exposes table schema for validation | So the validator can confirm `permitted_tables` actually exist, catching config typos early |
| Executes a validated query read-only | Opens the execution connection in SQLite's read-only URI mode — independent of the AST check, per FR-004 |
| Enforces the per-query timeout | Cancels/raises on a query exceeding the configured limit (FR-005) |

## State / Lifecycle

None of these entities are persisted or carry a lifecycle — each `ScopedQueryRequest` is
produced and resolved within a single tool call, consistent with how `TicketingAdapter`'s
tools already work (the only persisted state is the underlying seeded dataset itself, which is
fixed at MVP scope, not mutated — this skill never writes).
