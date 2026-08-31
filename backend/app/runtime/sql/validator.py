from dataclasses import dataclass, field

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

_READ_ONLY_STATEMENT_TYPES = (exp.Select,)


@dataclass(frozen=True)
class ScopedQueryRequest:
    """The input to validation: an LLM-generated candidate query plus the
    calling agent's permitted table scope. `candidate_sql` is always
    untrusted (Constitution Principle 7 / FR-009)."""

    question: str
    candidate_sql: str
    permitted_tables: frozenset[str]


@dataclass(frozen=True)
class QueryValidationResult:
    """The outcome of validating a candidate query, before any execution is
    attempted. `allowed=False` on any write/DDL statement, any out-of-scope
    table reference, or any parse failure - never a silent allow."""

    allowed: bool
    reason: str | None
    referenced_tables: list[str] = field(default_factory=list)
    statement_type: str = "UNKNOWN"


@dataclass(frozen=True)
class QueryResultSet:
    """The successful, executed result of a permitted query. An empty
    `rows` list with `row_count=0` is a valid success, not a failure."""

    columns: list[str]
    rows: list[dict]
    row_count: int


def validate(request: ScopedQueryRequest) -> QueryValidationResult:
    """Validate a candidate query via full AST parsing (never keyword/pattern
    matching - see research.md). Fail-closed: any parse failure, any
    non-SELECT statement, any multi-statement input, or any out-of-scope
    table reference results in denial.
    """
    try:
        statements = list(sqlglot.parse(request.candidate_sql))
    except ParseError as exc:
        return QueryValidationResult(
            allowed=False,
            reason=f"query failed to parse: {exc}",
        )

    statements = [s for s in statements if s is not None]
    if len(statements) != 1:
        return QueryValidationResult(
            allowed=False,
            reason="only a single SQL statement is permitted per query",
            statement_type="MULTIPLE" if len(statements) > 1 else "EMPTY",
        )

    statement = statements[0]
    statement_type = type(statement).__name__.upper()

    if not isinstance(statement, _READ_ONLY_STATEMENT_TYPES):
        return QueryValidationResult(
            allowed=False,
            reason=f"only read-only SELECT queries are permitted, got {statement_type}",
            statement_type=statement_type,
        )

    cte_names = {cte.alias for cte in statement.find_all(exp.CTE)}
    referenced_tables = sorted(
        {table.name for table in statement.find_all(exp.Table)} - cte_names
    )
    out_of_scope = [t for t in referenced_tables if t not in request.permitted_tables]
    if out_of_scope:
        return QueryValidationResult(
            allowed=False,
            reason=f"query references table(s) outside permitted scope: {', '.join(out_of_scope)}",
            referenced_tables=referenced_tables,
            statement_type=statement_type,
        )

    return QueryValidationResult(
        allowed=True,
        reason=None,
        referenced_tables=referenced_tables,
        statement_type=statement_type,
    )
