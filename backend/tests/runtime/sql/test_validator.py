import pytest

from app.runtime.sql.validator import ScopedQueryRequest, validate

PERMITTED = frozenset({"tickets"})


def _request(sql: str, permitted: frozenset[str] = PERMITTED) -> ScopedQueryRequest:
    return ScopedQueryRequest(question="n/a", candidate_sql=sql, permitted_tables=permitted)


# --- US1: correct, permitted read-only queries are allowed ---


def test_allows_simple_permitted_select():
    result = validate(_request("SELECT * FROM tickets WHERE status = 'open'"))
    assert result.allowed is True
    assert result.reason is None
    assert result.referenced_tables == ["tickets"]
    assert result.statement_type == "SELECT"


def test_cte_alias_is_not_treated_as_an_out_of_scope_table():
    """Regression test: a WITH-clause CTE name (e.g. `cnt`) is a query-local
    alias, not a real table, and must not be flagged as out-of-scope."""
    sql = (
        "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM cnt WHERE x < 10) "
        "SELECT COUNT(*) FROM cnt"
    )
    result = validate(_request(sql, permitted=frozenset({"tickets"})))
    assert result.allowed is True
    assert result.referenced_tables == []


def test_cte_wrapping_a_real_out_of_scope_table_is_still_denied():
    sql = "WITH recent AS (SELECT * FROM internal_payroll) SELECT * FROM recent"
    result = validate(_request(sql, permitted=frozenset({"tickets"})))
    assert result.allowed is False
    assert "internal_payroll" in result.reason


def test_allows_select_referencing_only_permitted_tables_in_join():
    result = validate(
        _request(
            "SELECT a.id FROM tickets a JOIN tickets b ON a.id = b.id",
            permitted=frozenset({"tickets"}),
        )
    )
    assert result.allowed is True


# --- US2: every write/DDL statement type is denied, with a clear reason ---


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO tickets (id) VALUES ('X')",
        "UPDATE tickets SET status = 'closed'",
        "DELETE FROM tickets",
        "CREATE TABLE evil (id TEXT)",
        "ALTER TABLE tickets ADD COLUMN evil TEXT",
        "DROP TABLE tickets",
        "TRUNCATE TABLE tickets",
    ],
)
def test_denies_every_write_and_ddl_statement_type(sql):
    result = validate(_request(sql))
    assert result.allowed is False
    assert result.reason is not None
    assert "read-only" in result.reason.lower() or "select" in result.reason.lower()


def test_denies_multi_statement_input():
    result = validate(_request("SELECT * FROM tickets; DROP TABLE tickets;"))
    assert result.allowed is False
    assert "single sql statement" in result.reason.lower()


def test_denies_unparseable_query():
    result = validate(_request("SELEKT * FRUM tickets GARBAGE"))
    assert result.allowed is False
    assert "failed to parse" in result.reason.lower()


def test_denial_reason_is_specific_not_generic():
    write_result = validate(_request("DELETE FROM tickets"))
    multi_result = validate(_request("SELECT 1; SELECT 2;"))
    assert write_result.reason != multi_result.reason  # each denial type is distinguishable


# --- US3: out-of-scope table references are denied, including mixed-scope joins ---


def test_denies_out_of_scope_single_table():
    result = validate(_request("SELECT * FROM internal_payroll", permitted=frozenset({"tickets"})))
    assert result.allowed is False
    assert "internal_payroll" in result.reason
    assert "outside permitted scope" in result.reason


def test_denies_mixed_scope_join_entirely():
    result = validate(
        _request(
            "SELECT a.id FROM tickets a JOIN internal_payroll b ON a.requester = b.employee_id",
            permitted=frozenset({"tickets"}),
        )
    )
    assert result.allowed is False
    assert "internal_payroll" in result.reason
    # the permitted table must not make it partially allowed
    assert result.referenced_tables == ["internal_payroll", "tickets"]
