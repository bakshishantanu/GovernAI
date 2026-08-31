import os

import pytest

from app.runtime.sql.adapter import SqlDataAdapter, SqlQueryTimeoutError

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
    adapter = SqlDataAdapter(seed_sql=_SEED_SQL, timeout_seconds=10.0)
    yield adapter
    os.remove(adapter._db_path)


def test_seeded_data_is_queryable(adapter):
    result = adapter.execute("SELECT COUNT(*) AS count FROM tickets WHERE status = 'open'")
    assert result.columns == ["count"]
    assert result.rows == [{"count": 2}]
    assert result.row_count == 1


def test_table_names_reflects_seeded_schema(adapter):
    assert adapter.table_names() == {"tickets", "internal_payroll"}


def test_empty_result_is_a_valid_success(adapter):
    result = adapter.execute("SELECT * FROM tickets WHERE id = 'TCK-9999'")
    assert result.rows == []
    assert result.row_count == 0


def test_execute_connection_rejects_writes_at_db_level(adapter):
    with pytest.raises(PermissionError, match="read-only"):
        adapter.execute("INSERT INTO tickets (id, subject, status, requester) VALUES ('X', 'x', 'open', 'x')")

    # prove the write genuinely did not happen
    result = adapter.execute("SELECT COUNT(*) AS count FROM tickets")
    assert result.rows == [{"count": 3}]


def test_slow_query_is_stopped_by_timeout():
    adapter = SqlDataAdapter(seed_sql=_SEED_SQL, timeout_seconds=0.2)
    try:
        with pytest.raises(SqlQueryTimeoutError):
            adapter.execute(
                "WITH RECURSIVE cnt(x) AS "
                "(SELECT 1 UNION ALL SELECT x + 1 FROM cnt WHERE x < 100000000) "
                "SELECT COUNT(*) FROM cnt"
            )
    finally:
        os.remove(adapter._db_path)
