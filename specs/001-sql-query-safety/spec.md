# Feature Specification: SQL Query Skill

**Feature Branch**: `001-sql-query-safety`

**Created**: 2026-08-31

**Status**: Draft

**Input**: User description: "build the sql skill. The SQL agent must run only read-only, scoped queries against permitted tables and reject any write or schema-altering query before it reaches the database."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Answer a data question correctly (Priority: P1)

An agent is given a question that requires looking up or computing something from structured
data (e.g. "how many tickets were opened last week?"). It runs a read-only, scoped query against
permitted data and returns a correct, computed answer — not a guess.

**Why this priority**: This is the entire reason the skill exists. Without it, there is no SQL
skill — just a safety layer with nothing to protect.

**Independent Test**: Given a seeded dataset and a question requiring computation, the agent
produces the correct answer, and exactly one read query was executed to get it.

**Acceptance Scenarios**:

1. **Given** a seeded dataset the agent is permitted to query, **When** the agent is asked a
   question answerable from that data, **Then** it returns a correct, computed answer.
2. **Given** a query with no matching rows, **When** it runs, **Then** the agent reports "no
   results found" rather than treating the empty result as a failure.

---

### User Story 2 - Block any write or schema-altering query (Priority: P1)

Regardless of what the agent "intends" to do, any query that would write data or alter schema
(insert, update, delete, or any DDL) is rejected before it reaches the database.

**Why this priority**: This is the explicit safety guarantee the feature was requested for. A
SQL skill that can accidentally or deliberately write data is not an MVP-acceptable feature —
it's a data-integrity incident waiting to happen.

**Independent Test**: Submit a query containing a write or schema-altering operation and confirm
it never reaches the database — it is rejected before execution, with a clear reason returned
instead of a database-level error.

**Acceptance Scenarios**:

1. **Given** a candidate query containing INSERT, UPDATE, or DELETE, **When** it is submitted,
   **Then** it is rejected before execution and the agent is told why.
2. **Given** a candidate query containing DDL (CREATE, ALTER, DROP, TRUNCATE), **When** it is
   submitted, **Then** it is rejected before execution and the agent is told why.
3. **Given** a rejected query, **When** the rejection is recorded, **Then** it appears in the
   platform's audit trail as a policy denial with a human-readable reason.

---

### User Story 3 - Stay within permitted tables (Priority: P2)

An agent can only query the tables/data it has been explicitly permitted to access — never
data belonging to a different scope, dataset, or team.

**Why this priority**: Without this, an agent scoped to one dataset could read another team's
data simply by asking a question that touches it — a data-isolation failure, not just a
data-integrity one.

**Independent Test**: An agent permitted only for one dataset attempts a question that would
require querying a table outside that scope; the query is blocked before execution.

**Acceptance Scenarios**:

1. **Given** an agent permitted only for Table A, **When** it attempts a query referencing
   Table B, **Then** the query is rejected before execution.
2. **Given** a query that joins a permitted table with a non-permitted table, **When** it is
   submitted, **Then** the entire query is rejected — not partially executed against only the
   permitted part.

---

### Edge Cases

- A query is syntactically invalid — the agent receives a clear error, not a raw database
  stack trace.
- A query is read-only in form but disguises a write via a nested call or a second statement
  (multi-statement input) — it MUST still be rejected.
- A query would run long enough to be a resource risk (e.g. an unbounded scan) — it is stopped
  by a timeout rather than allowed to run indefinitely.
- A query is well-formed and fully in-scope, but the underlying data has zero matching rows —
  this is a successful query with an empty result, not a denial or an error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a natural-language question intended to be answered from
  structured data.
- **FR-002**: The system MUST validate every candidate query before execution and reject it if
  it contains any write operation (INSERT, UPDATE, DELETE) or schema-altering operation (CREATE,
  ALTER, DROP, TRUNCATE, or equivalent DDL).
- **FR-003**: The system MUST reject a candidate query that references any table outside the
  requesting agent's permitted scope, before execution — including queries that join a permitted
  table with a non-permitted one.
- **FR-004**: The system MUST execute permitted, read-only queries using a database connection
  that itself has no write privileges, as an independent second layer of protection beyond
  query validation.
- **FR-005**: The system MUST enforce an execution timeout and report a clear timeout error if a
  query exceeds it, rather than allowing it to run indefinitely.
- **FR-006**: Every rejected query (write attempt, out-of-scope table, or timeout) MUST be
  recorded with a human-readable reason, consistent with the platform's existing audit logging.
- **FR-007**: The system MUST return successful query results in a structured form usable to
  compose a natural-language answer.
- **FR-008**: The system MUST distinguish "query succeeded with zero matching rows" from "query
  was denied" so the agent never misreports one as the other.
- **FR-009**: System MUST translate a natural-language question into a candidate query by having
  the LLM generate SQL text directly. This generated SQL MUST always be treated as untrusted
  input — it MUST pass all validation (FR-002, FR-003, FR-010) and governance checks before
  execution, never executed on the basis of the LLM having "intended" something safe.
- **FR-010**: System MUST validate that a candidate query is read-only and in-scope using full
  SQL parsing (building and inspecting an abstract syntax tree), not a keyword or pattern-based
  check — so that disguised, obfuscated, or multi-statement write attempts are structurally
  detected rather than relying on literal keyword matches.
- **FR-011**: "Permitted tables" for an agent MUST be determined by fine-grained, per-table
  permissions (e.g. a distinct permission per table/dataset, consistent with the platform's
  existing `resource:action` permission model) — not a single fixed dataset bound to a skill
  instance. This allows one SQL skill to serve multiple agents, each with its own permitted
  scope.

### Key Entities

- **Scoped Query Request**: A natural-language question together with the requesting agent's
  permitted table scope.
- **Query Validation Result**: The outcome of checking a candidate query before execution —
  allowed, or denied with a reason.
- **Query Result Set**: The structured rows returned by a permitted, executed query.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A well-scoped question about permitted data returns a correct, computed answer.
- **SC-002**: 100% of attempted write or schema-altering queries, across every write/DDL
  operation type, are blocked before reaching the database.
- **SC-003**: 100% of queries referencing any out-of-scope table — including joins mixing
  permitted and non-permitted tables — are blocked before execution.
- **SC-004**: Every blocked query produces a clear, human-readable denial reason visible in the
  audit trail, never a raw database error surfaced to the agent or user.
- **SC-005**: A query that would run past the configured timeout is stopped and reported as a
  timeout rather than left running.

## Assumptions

- The underlying structured dataset already exists in queryable form (e.g. seeded tables);
  data ingestion/import into that dataset is out of scope for this feature.
- A per-query timeout applies; the exact duration is a configuration value, not a fixed
  requirement of this spec.
- This skill never writes data or alters schema under any circumstance — write capability is not
  a future extension of this feature, it is permanently out of scope by design.
- The platform's existing audit-logging mechanism is reused for recording denials; this feature
  does not introduce a separate logging path.
