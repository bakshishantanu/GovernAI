---

description: "Task list template for feature implementation"
---

# Tasks: SQL Query Skill

**Input**: Design documents from `specs/001-sql-query-safety/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all present)

**Tests**: Included. Not explicitly requested in spec.md, but the project's own constitution
(Development Workflow section) requires "New code ships with automated tests; a feature is not
considered done until its tests pass locally" — and every prior skill/provider in this repo
(Groq/Gemini providers, circuit breaker, LLM service, Ticketing skill) shipped with tests as
standard practice. Skipping tests here would be inconsistent with established project practice.

**Organization**: Tasks are grouped by user story (US1/US2/US3, matching spec.md's priorities)
so each can be implemented and independently tested.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact, matching plan.md's Project Structure

---

## Phase 1: Setup

**Purpose**: Get the new dependency in place before any code depends on it.

- [X] T001 Add `sqlglot` to `backend/pyproject.toml` dependencies (research.md's AST-parsing decision)
- [X] T002 Install updated dependencies in `backend/.venv` and verify `import sqlglot` works (depends on T001)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared data shapes and the storage adapter every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Define `ScopedQueryRequest`, `QueryValidationResult`, `QueryResultSet` dataclasses (data-model.md) in `backend/app/runtime/sql/validator.py`
- [X] T004 [P] Create seeded mock dataset + `SqlDataAdapter` class (schema introspection, write connection for seeding) in `backend/app/runtime/sql/adapter.py`
- [X] T005 Implement read-only execution in `SqlDataAdapter`: open a second, SQLite read-only URI-mode (`file:...?mode=ro`) connection; execute a query and return a `QueryResultSet`, in `backend/app/runtime/sql/adapter.py` (depends on T004)
- [X] T006 Implement per-query timeout enforcement in `SqlDataAdapter.execute()`, config-driven default 10s (research.md), in `backend/app/runtime/sql/adapter.py` (depends on T005)
- [X] T007 Unit tests for `SqlDataAdapter` — seeded data is queryable, the read-only connection actually rejects a raw write attempt at the DB level, a slow query is stopped by the timeout — in `backend/tests/runtime/sql/test_adapter.py` (depends on T006)

**Checkpoint**: Foundation ready — user story implementation can now begin.

---

## Phase 3: User Story 1 - Answer a data question correctly (Priority: P1) 🎯 MVP

**Goal**: An agent submits LLM-generated SQL; it's confirmed to be a read-only SELECT, executed,
and a correct (or correctly-empty) answer is returned.

**Independent Test**: Given a seeded dataset and a question requiring computation, the agent
gets a correct computed answer; a query with zero matching rows is reported as a successful
empty result, not a failure.

### Implementation for User Story 1

- [X] T008 [US1] Implement basic statement-type validation (SELECT-only, via `sqlglot` parse) — `validate()` returning `QueryValidationResult` — in `backend/app/runtime/sql/validator.py` (depends on T003)
- [X] T009 [US1] Implement `SqlQuerySkill` + `RunSqlQueryTool` in `backend/app/skills/sql_query.py`: parse tool args → `validate()` → on allow, `adapter.execute()` → format `QueryResultSet` into the success shape from `contracts/run_sql_query_tool.md` (depends on T006, T008)
- [X] T010 [US1] Unit tests: correct computed answer for a well-scoped SELECT question, and an empty result reported as `success: true, row_count: 0` rather than an error, in `backend/tests/skills/test_sql_query.py` (depends on T009)

**Checkpoint**: User Story 1 is fully functional and independently testable — the happy path works end-to-end.

---

## Phase 4: User Story 2 - Block any write or schema-altering query (Priority: P1)

**Goal**: Every write or schema-altering statement is rejected before it reaches the database,
with a clear, human-readable reason.

**Independent Test**: Submit queries containing INSERT/UPDATE/DELETE and DDL (CREATE/ALTER/DROP/
TRUNCATE); confirm each is denied before execution, distinctly from each other and from a parse
failure.

### Implementation for User Story 2

- [X] T011 [US2] Extend the validator to detect and deny every non-SELECT statement type (INSERT/UPDATE/DELETE/DDL), setting `QueryValidationResult.reason`, in `backend/app/runtime/sql/validator.py` (depends on T008)
- [X] T012 [US2] Extend the validator to reject multi-statement input (a second statement smuggled in) and any unparseable query as a denial — never an "allow because unsure" — in `backend/app/runtime/sql/validator.py` (depends on T011)
- [X] T013 [US2] Wire denial reasons into `RunSqlQueryTool`'s `denied` output shape (`contracts/run_sql_query_tool.md`) in `backend/app/skills/sql_query.py` (depends on T009, T012)
- [X] T014 [P] [US2] Unit tests: every write/DDL statement type is denied before execution with a distinct, human-readable reason, in `backend/tests/runtime/sql/test_validator.py` (depends on T012)
- [X] T015 [P] [US2] Unit test: a denied query never reaches `SqlDataAdapter.execute()` (assert via call count/mock), in `backend/tests/skills/test_sql_query.py` (depends on T013)

**Checkpoint**: User Stories 1 + 2 both work — the skill is now safe against writes.

---

## Phase 5: User Story 3 - Stay within permitted tables (Priority: P2)

**Goal**: Any query referencing a table outside the agent's permitted scope is rejected, including
a JOIN that mixes permitted and non-permitted tables.

**Independent Test**: An agent permitted only for Table A attempts a query on Table B (or a JOIN
of A and B); the query is denied before execution.

### Implementation for User Story 3

- [X] T016 [US3] Extract every referenced table from the parsed AST in `backend/app/runtime/sql/validator.py` (depends on T008)
- [X] T017 [US3] Implement the scope check — deny if any referenced table isn't in `permitted_tables`, including partial-JOIN cases — in `backend/app/runtime/sql/validator.py` (depends on T016)
- [X] T018 [US3] Wire an agent's `sql:read:<table>` permissions into `permitted_tables` at `SqlQuerySkill` construction, in `backend/app/skills/sql_query.py` (depends on T017)
- [X] T019 [P] [US3] Unit tests: an out-of-scope single-table query is denied, and a mixed-scope JOIN is denied entirely rather than partially executed, in `backend/tests/runtime/sql/test_validator.py` (depends on T017)

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Guarantees that cut across all three stories (Constitution Principle 7).

- [X] T020 [P] Unit test: raw database driver exceptions never leak into tool output — only the `success`/`denied`/`timeout` shapes from `contracts/run_sql_query_tool.md` ever appear — in `backend/tests/skills/test_sql_query.py`
- [X] T021 [P] Unit test: no credential or connection-string value ever appears in any tool output, in `backend/tests/skills/test_sql_query.py`
- [X] T022 Run `quickstart.md` end-to-end and confirm every item in `specs/001-sql-query-safety/checklists/requirements.md` still holds

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational; US1/US2/US3 can be worked in parallel
  by different people once Foundational is done, though US2/US3 both extend `validator.py`
  (same file as US1's T008), so within a single person's work they're naturally sequential
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **US1 (P1)**: Starts after Foundational. No dependency on US2/US3.
- **US2 (P1)**: Starts after Foundational. Extends the same `validator.py` file US1 created
  (T008) — sequential with US1 if done by one person, independent in principle otherwise.
- **US3 (P2)**: Starts after Foundational. Also extends `validator.py` (T008) — same note as US2.

### Parallel Opportunities

- T003 and T004 (Foundational) — different files, no shared dependency
- T014 and T015 (US2 tests) — different files, both dependencies satisfied by that point
- T019 (US3 test) and T018 (US3 skill wiring) — different files, both depend only on T017
- T020 and T021 (Polish) — different tasks in the same test file are listed together but should
  be applied as one edit pass rather than two simultaneous edits to avoid overwriting each other

---

## Parallel Example: Foundational Phase

```
Task: "Define ScopedQueryRequest, QueryValidationResult, QueryResultSet dataclasses in backend/app/runtime/sql/validator.py"
Task: "Create seeded mock dataset + SqlDataAdapter class in backend/app/runtime/sql/adapter.py"
```

---

## Implementation Strategy

### MVP Scope: User Story 1 **and** User Story 2 together

Unlike a typical spec-kit MVP (usually just the single P1 story), this spec's own priorities
mark **both** US1 and US2 as P1 — a query-execution skill that can answer questions but cannot
yet block writes is not an acceptable MVP for a governance-focused platform (Constitution
Principle 5, Fail-Closed by Default). Treat Phases 1-4 together as the MVP; US3's table-scoping
(Phase 5) is the next increment, not part of the minimum safe slice.

### Incremental Delivery

1. Setup + Foundational → adapter and data shapes ready
2. US1 → correct answers work → **not yet safe to demo with untrusted input**
3. US2 → writes are blocked → **MVP: safe to demo**
4. US3 → table scoping enforced → full spec delivered
5. Polish → credential/exception leakage guarantees verified

---

## Notes

- [P] tasks touch different files with no incomplete dependency
- [Story] labels map every implementation/test task to its user story for traceability
- Commit after each phase checkpoint, not after every single task — mirrors how this project's
  other features (Ticketing skill, LLM service) were committed as coherent logical chunks
- Run the full `backend` test suite (not just this feature's new tests) before considering any
  phase checkpoint truly done, per this project's established practice this session
