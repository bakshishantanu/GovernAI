from __future__ import annotations
import os
import sqlite3
import tempfile
import time
from pathlib import Path

from app.runtime.sql.validator import QueryResultSet


class SqlQueryTimeoutError(Exception):
    """Raised when a query exceeds its configured execution time limit."""


class SqlExecutionError(Exception):
    """Raised when a validated query still fails at actual execution time
    (e.g. a semantic error like a missing column). Deliberately generic -
    never carries the raw driver exception text to the caller."""


class SqlDataAdapter:
    """Mock, seeded SQLite backend for the SQL Query Skill (MVP - see
    research.md). Execution always goes through a read-only connection, as
    an independent second layer of protection beneath query validation
    (FR-004): even a query that somehow slipped past validation still
    cannot write, because the connection itself has no write capability.
    """

    def __init__(
        self,
        seed_sql: str,
        db_path: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._db_path = db_path or self._make_temp_db_path()
        self._timeout_seconds = timeout_seconds
        self._seed(seed_sql)

    @staticmethod
    def _make_temp_db_path() -> str:
        fd, path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        return path

    def _seed(self, seed_sql: str) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.executescript(seed_sql)
            conn.commit()
        finally:
            conn.close()

    def table_names(self) -> set[str]:
        conn = sqlite3.connect(self._db_path)
        try:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            return {row[0] for row in rows}
        finally:
            conn.close()

    def execute(self, sql: str) -> QueryResultSet:
        uri = f"file:{Path(self._db_path).as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        deadline = time.monotonic() + self._timeout_seconds
        conn.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 1000)

        try:
            cursor = conn.execute(sql)
            columns = [d[0] for d in cursor.description] if cursor.description else []
            rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            return QueryResultSet(columns=columns, rows=rows, row_count=len(rows))
        except sqlite3.OperationalError as exc:
            message = str(exc).lower()
            if "interrupted" in message:
                raise SqlQueryTimeoutError(
                    f"query exceeded the {self._timeout_seconds}s execution limit"
                ) from exc
            if "readonly" in message:
                raise PermissionError(f"write rejected by read-only connection: {exc}") from exc
            raise SqlExecutionError("query could not be executed against the database") from exc
        except sqlite3.Error as exc:
            raise SqlExecutionError("query could not be executed against the database") from exc
        finally:
            conn.close()
