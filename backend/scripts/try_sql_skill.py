"""Interactively try the SQL Query Skill against its seeded demo data.

Run: .venv/Scripts/python.exe scripts/try_sql_skill.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.skills.sql_query import SqlQuerySkill

SCHEMA_HINT = """
Seeded tables in this demo database:

  tickets(id, subject, status, requester)          <- permitted, you can query this
  internal_payroll(employee_id, salary)             <- NOT permitted, watch it get denied

Try things like:
  SELECT * FROM tickets
  SELECT COUNT(*) FROM tickets WHERE status = 'open'
  DELETE FROM tickets                                (will be denied - write attempt)
  SELECT * FROM internal_payroll                     (will be denied - out of scope)
  SELECT * FROM tickets; DROP TABLE tickets;          (will be denied - multi-statement)

Type 'quit' to exit.
"""


async def main() -> None:
    skill = SqlQuerySkill(permitted_tables={"tickets"})
    tool = skill.get_tools()[0]
    print(SCHEMA_HINT)

    while True:
        sql = input("\nSQL> ").strip()
        if sql.lower() in ("quit", "exit"):
            break
        if not sql:
            continue
        result = await tool.execute(question="interactive test", sql=sql)
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
