"""The seed script must derive permissions the same way the product does.

Hand-written permissions are what let the seeded database disagree with every
agent the console builds (D-043): four permissions on one agent and none on any
other, which is the state the live database was found in.
"""

import importlib.util
import pathlib
import uuid
from unittest.mock import AsyncMock, MagicMock

import app.domain.agents.models  # noqa: F401  -- completes the mapper registry
import app.domain.permissions.models  # noqa: F401

_SEED = pathlib.Path(__file__).resolve().parents[2] / "scripts" / "seed_demo_data.py"


def _seed_module():
    spec = importlib.util.spec_from_file_location("seed_demo_data", _SEED)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _session_returning(permissions):
    session = AsyncMock()
    session.execute.return_value = MagicMock(
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=permissions)))
    )
    session.add = MagicMock()
    return session


async def test_grants_the_union_of_the_skills_permissions():
    seed = _seed_module()
    passport_id = uuid.uuid4()
    # ticket:read is declared by two of the bound skills; it must be granted once.
    session = _session_returning(
        ["ticket:read", "ticket:create", "ticket:read", "sql:read:tickets"]
    )

    await seed.derive_permissions(session, passport_id, ["ticketing", "sql_query"])

    granted = [c.args[0] for c in session.add.call_args_list]
    assert [p.permission for p in granted] == ["sql:read:tickets", "ticket:create", "ticket:read"]
    assert {p.passport_id for p in granted} == {passport_id}


async def test_grants_nothing_for_an_agent_with_no_skills():
    seed = _seed_module()
    session = _session_returning([])

    await seed.derive_permissions(session, uuid.uuid4(), [])

    session.execute.assert_not_awaited()
    session.add.assert_not_called()
