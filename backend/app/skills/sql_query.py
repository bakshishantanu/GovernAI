from __future__ import annotations
from app.runtime.sql.adapter import SqlDataAdapter, SqlExecutionError, SqlQueryTimeoutError
from app.runtime.sql.validator import ScopedQueryRequest, validate
from app.skills.base import BaseSkill, BaseTool, TrustLevel

_DEFAULT_SEED_SQL = """
CREATE TABLE tickets (id TEXT PRIMARY KEY, subject TEXT, status TEXT, requester TEXT);
INSERT INTO tickets (id, subject, status, requester) VALUES
    ('TCK-1001', 'Cannot reset password', 'open', 'alice@example.com'),
    ('TCK-1002', 'Invoice mismatch', 'open', 'bob@example.com'),
    ('TCK-1003', 'Feature request: dark mode', 'closed', 'carol@example.com');

CREATE TABLE internal_payroll (employee_id TEXT PRIMARY KEY, salary INTEGER);
INSERT INTO internal_payroll (employee_id, salary) VALUES ('E1', 90000);
"""


class RunSqlQueryTool(BaseTool):
    name = "run_sql_query"
    description = (
        "Answer a question requiring computation over structured data by running a "
        "read-only, scoped SQL query."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The natural-language question to answer from structured data.",
            },
            "sql": {
                "type": "string",
                "description": (
                    "A single read-only SQL SELECT statement answering the question, "
                    "referencing only permitted tables."
                ),
            },
        },
        "required": ["question", "sql"],
    }

    def __init__(self, adapter: SqlDataAdapter, permitted_tables: frozenset[str]) -> None:
        self._adapter = adapter
        self._permitted_tables = permitted_tables
        # Coarse-grained gate for the registry/governance middleware. Fine-grained,
        # per-query table enforcement happens inside validate() regardless - this
        # is metadata, not the actual security boundary.
        self.required_permission = ",".join(f"sql:read:{t}" for t in sorted(permitted_tables))

    async def execute(self, **kwargs) -> dict:
        request = ScopedQueryRequest(
            question=kwargs["question"],
            candidate_sql=kwargs["sql"],
            permitted_tables=self._permitted_tables,
        )
        validation = validate(request)
        if not validation.allowed:
            return {
                "success": False,
                "error": "denied",
                "reason": validation.reason,
                "statement_type": validation.statement_type,
            }

        try:
            result = self._adapter.execute(request.candidate_sql)
        except SqlQueryTimeoutError as exc:
            return {"success": False, "error": "timeout", "reason": str(exc)}
        except PermissionError:
            # Second-layer defense (FR-004) triggered - should not normally happen if
            # validation above is correct, but never leak the raw driver exception.
            return {
                "success": False,
                "error": "denied",
                "reason": "query rejected by the database's read-only connection",
            }
        except SqlExecutionError as exc:
            return {"success": False, "error": "execution_failed", "reason": str(exc)}

        return {
            "success": True,
            "columns": result.columns,
            "rows": result.rows,
            "row_count": result.row_count,
        }


class SqlQuerySkill(BaseSkill):
    name = "sql_query"
    display_name = "SQL Query"
    description = "Answer questions over structured data via scoped, read-only SQL queries."
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED

    def __init__(
        self,
        permitted_tables: set[str] | frozenset[str],
        adapter: SqlDataAdapter | None = None,
    ) -> None:
        self._permitted_tables = frozenset(permitted_tables)
        self._adapter = adapter or SqlDataAdapter(seed_sql=_DEFAULT_SEED_SQL)
        self.required_permissions = [f"sql:read:{table}" for table in sorted(self._permitted_tables)]

    def get_tools(self) -> list[BaseTool]:
        return [RunSqlQueryTool(self._adapter, self._permitted_tables)]
