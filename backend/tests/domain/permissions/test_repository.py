"""PermissionRepository behaviour the compliance check depends on.

AsyncMock in the style of tests/test_agent_service.py: these assert the
repository asks for the right thing and shapes the result correctly, not that
Postgres works.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Permission.passport is a relationship to AgentPassport, and SQLAlchemy
# resolves that name through its declarative registry at mapper-configuration
# time. Importing only the permissions module leaves the registry incomplete,
# so the mapper cannot be built. main.py imports every model for exactly this
# reason; a focused test has to do the same.
import app.domain.agents.models  # noqa: F401
from app.domain.permissions.models import ForbiddenPermissionPair
from app.domain.permissions.repository import PermissionRepository


def _repo_returning(rows):
    session = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    session.execute.return_value = result
    return PermissionRepository(session)


async def test_list_forbidden_pairs_returns_triples():
    row = ForbiddenPermissionPair(
        id=uuid4(),
        permission_a="sql:read:internal_payroll",
        permission_b="docs:search:public",
        reason="payroll + public surface",
        enabled=True,
    )
    pairs = await _repo_returning([row]).list_forbidden_pairs()
    assert pairs == [
        ("sql:read:internal_payroll", "docs:search:public", "payroll + public surface")
    ]


async def test_list_forbidden_pairs_empty_when_no_rows():
    assert await _repo_returning([]).list_forbidden_pairs() == []
