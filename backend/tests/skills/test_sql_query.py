import os

import pytest

from app.runtime.sql.adapter import SqlDataAdapter
from app.skills.sql_query import RunSqlQueryTool, SqlQuerySkill

_SEED_SQL = """
CREATE TABLE tickets (id TEXT PRIMARY KEY, subject TEXT, status TEXT, requester TEXT);
INSERT INTO tickets (id, subject, status, requester) VALUES
    ('TCK-1001', 'Cannot reset password', 'open', 'alice@example.com'),
    ('TCK-1002', 'Invoice mismatch', 'open', 'bob@example.com'),
    ('TCK-1003', 'Feature request: dark mode', 'closed', 'carol@example.com');

CREATE TABLE internal_payroll (employee_id TEXT PRIMARY KEY, salary INTEGER);
INSERT INTO internal_payroll (employee_id, salary) VALUES ('E1', 90000);
"""


@pytest.fixture
def adapter():
    a = SqlDataAdapter(seed_sql=_SEED_SQL, timeout_seconds=10.0)
    yield a
    os.remove(a._db_path)


@pytest.fixture
def skill(adapter):
    return SqlQuerySkill(permitted_tables={"tickets"}, adapter=adapter)


# --- Skill metadata (FR-011: per-table, per-instance permissions) ---


def test_skill_declares_per_table_permissions(skill):
    assert skill.required_permissions == ["sql:read:tickets"]


def test_skill_exposes_the_run_sql_query_tool(skill):
    tools = skill.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "run_sql_query"


# --- US1: correct answers, including the empty-result-is-success case ---


async def test_correct_computed_answer_for_permitted_question(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(
        question="how many tickets are open?",
        sql="SELECT COUNT(*) AS count FROM tickets WHERE status = 'open'",
    )
    assert result == {"success": True, "columns": ["count"], "rows": [{"count": 2}], "row_count": 1}


async def test_empty_result_reported_as_success_not_denial(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(question="find ticket X", sql="SELECT * FROM tickets WHERE id = 'NOPE'")
    assert result["success"] is True
    assert result["row_count"] == 0
    assert result["rows"] == []


# --- US2/US3: denials never reach the database ---


class _NeverCallAdapter:
    """Fails the test loudly if execute() is ever called - proves a denied
    query never reaches the database (tasks.md T015)."""

    def execute(self, sql):
        raise AssertionError(f"adapter.execute() should never be called for a denied query, got: {sql}")


async def test_write_query_is_denied_and_never_reaches_the_adapter():
    tool = RunSqlQueryTool(_NeverCallAdapter(), frozenset({"tickets"}))
    result = await tool.execute(question="close everything", sql="UPDATE tickets SET status = 'closed'")
    assert result["success"] is False
    assert result["error"] == "denied"
    assert "read-only" in result["reason"].lower() or "select" in result["reason"].lower()


async def test_out_of_scope_query_is_denied_and_never_reaches_the_adapter():
    tool = RunSqlQueryTool(_NeverCallAdapter(), frozenset({"tickets"}))
    result = await tool.execute(question="show payroll", sql="SELECT * FROM internal_payroll")
    assert result["success"] is False
    assert result["error"] == "denied"
    assert "internal_payroll" in result["reason"]


# --- Polish: no raw exceptions, no credentials/paths ever leak into output ---


async def test_semantic_execution_error_returns_clean_error_not_raw_exception(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(question="bad column", sql="SELECT nonexistent_column FROM tickets")
    assert result["success"] is False
    assert result["error"] == "execution_failed"
    # never leak sqlite's raw driver message
    assert "sqlite3" not in result["reason"].lower()
    assert "operationalerror" not in result["reason"].lower()


async def test_timeout_returns_clean_error(adapter):
    slow_adapter = SqlDataAdapter(seed_sql=_SEED_SQL, timeout_seconds=0.2)
    try:
        tool = RunSqlQueryTool(slow_adapter, frozenset({"tickets"}))
        result = await tool.execute(
            question="slow",
            sql=(
                "WITH RECURSIVE cnt(x) AS "
                "(SELECT 1 UNION ALL SELECT x + 1 FROM cnt WHERE x < 100000000) "
                "SELECT COUNT(*) FROM cnt"
            ),
        )
        assert result == {
            "success": False,
            "error": "timeout",
            "reason": "query exceeded the 0.2s execution limit",
        }
    finally:
        os.remove(slow_adapter._db_path)


async def test_no_file_path_or_credential_ever_appears_in_any_output(skill, adapter):
    tool = skill.get_tools()[0]

    outputs = [
        await tool.execute(question="ok", sql="SELECT * FROM tickets"),
        await tool.execute(question="denied", sql="DROP TABLE tickets"),
        await tool.execute(question="scope", sql="SELECT * FROM internal_payroll"),
        await tool.execute(question="bad col", sql="SELECT nope FROM tickets"),
    ]
    for output in outputs:
        serialized = str(output)
        assert adapter._db_path not in serialized
        assert ".sqlite" not in serialized
