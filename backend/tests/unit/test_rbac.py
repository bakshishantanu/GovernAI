from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.schemas.auth import CurrentUser
from app.domain.auth.rbac import require_admin, require_role


def user(role: str) -> CurrentUser:
    return CurrentUser(id=uuid4(), org_id=uuid4(), role=role)


@pytest.mark.asyncio
async def test_admin_is_allowed_through():
    admin = user("admin")

    assert await require_admin(admin) is admin


@pytest.mark.asyncio
async def test_user_is_refused_with_403():
    """FRD-01's acceptance criterion: a user attempting an admin action gets 403."""
    with pytest.raises(HTTPException) as exc:
        await require_admin(user("agent_builder"))

    assert exc.value.status_code == 403
    assert "admin" in exc.value.detail


def test_unknown_role_cannot_even_be_constructed():
    """Defence in depth: the schema rejects any role outside the two we define,
    so an unrecognised role never reaches the dependency in the first place."""
    with pytest.raises(ValidationError):
        CurrentUser(id=uuid4(), org_id=uuid4(), role="superuser")


@pytest.mark.asyncio
async def test_require_role_admits_any_listed_role():
    dependency = require_role("admin", "agent_builder")

    for role in ("admin", "agent_builder"):
        assert (await dependency(user(role))).role == role
