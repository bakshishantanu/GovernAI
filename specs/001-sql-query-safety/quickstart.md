# Quickstart: SQL Query Skill

How to manually prove this feature works end-to-end once implemented (mirrors the pattern
already used for `backend/scripts/manual_llm_smoke_test.py`). This is a validation guide, not
an implementation — see `tasks.md` (from `/speckit-tasks`) for how it actually gets built.

## Prerequisites

- Backend venv set up (`backend/.venv`), per the existing project setup.
- No API keys needed — this feature has no external network dependency, it's local SQLite +
  local validation.

## 1. Automated tests (primary validation)

```
cd backend
.venv/Scripts/python.exe -m pytest tests/skills/test_sql_query.py tests/runtime/sql/ -v
```

Expected: all tests pass, covering (per spec.md's acceptance scenarios):
- A correctly-scoped, read-only question returns a correct computed answer (US1)
- Every write/DDL statement type is rejected before execution (US2)
- A query referencing an out-of-scope table — including a mixed-scope JOIN — is rejected (US3)
- An empty-but-valid result is reported as success, not denial (Edge Cases)
- A syntactically invalid query returns a clear error, not a raw exception (Edge Cases)
- A slow query is stopped by the timeout (Edge Cases)

## 2. Manual, interactive check

```python
import asyncio
from app.skills.sql_query import SqlQuerySkill

async def main():
    skill = SqlQuerySkill(permitted_tables={"tickets"})
    tool = skill.get_tools()[0]

    # Should succeed - permitted table, read-only
    print(await tool.execute(question="how many tickets are open?", sql="SELECT COUNT(*) AS count FROM tickets WHERE status = 'open'"))

    # Should be denied - write statement
    print(await tool.execute(question="close all tickets", sql="UPDATE tickets SET status = 'closed'"))

    # Should be denied - out-of-scope table
    print(await tool.execute(question="show me payroll", sql="SELECT * FROM internal_payroll"))

asyncio.run(main())
```

Expected output: one `"success": true` result with a real count, followed by two
`"success": false, "error": "denied"` results with distinct, human-readable `reason` fields.

## 3. What "done" looks like

- [ ] All items in `specs/001-sql-query-safety/checklists/requirements.md` still pass
- [ ] All automated tests above pass
- [ ] The manual check above produces exactly the expected allow/deny/deny pattern
- [ ] No database credentials or raw driver exceptions appear in any tool output (spot-check the
      denied/timeout JSON shapes against `contracts/run_sql_query_tool.md`)
