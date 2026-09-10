from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.schemas.auth import CurrentUser
from app.domain.auth.rbac import require_admin, require_builder, require_role, require_user


def user(role: str) -> CurrentUser:
    return CurrentUser(id=uuid4(), org_id=uuid4(), role=role)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_admin_is_allowed_through():
    admin = user("admin")
    assert await require_admin(admin) is admin


@pytest.mark.asyncio
async def test_builder_is_refused_with_403():
    """An agent builder attempting an admin action gets 403."""
    with pytest.raises(HTTPException) as exc:
        await require_admin(user("agent_builder"))

    assert exc.value.status_code == 403
    assert "admin" in exc.value.detail


@pytest.mark.asyncio
async def test_user_role_is_refused_with_403_for_admin():
    """A user attempting an admin action gets 403."""
    with pytest.raises(HTTPException) as exc:
        await require_admin(user("user"))

    assert exc.value.status_code == 403
    assert "admin" in exc.value.detail


def test_unknown_role_cannot_even_be_constructed():
    """Defence in depth: the schema rejects any role outside the supported set."""
    with pytest.raises(ValidationError):
        CurrentUser(id=uuid4(), org_id=uuid4(), role="superuser")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        CurrentUser(id=uuid4(), org_id=uuid4(), role="hacker")  # type: ignore[arg-type]

    # Valid supported roles construct without error
    assert CurrentUser(id=uuid4(), org_id=uuid4(), role="admin").role == "admin"
    assert CurrentUser(id=uuid4(), org_id=uuid4(), role="agent_builder").role == "agent_builder"
    assert CurrentUser(id=uuid4(), org_id=uuid4(), role="user").role == "user"


@pytest.mark.asyncio
async def test_require_builder_and_user_admit_both():
    """Both require_builder and require_user admit agent_builder and user interchangeably."""
    for u in (user("agent_builder"), user("user")):
        assert await require_builder(u) is u
        assert await require_user(u) is u


@pytest.mark.asyncio
async def test_require_role_admits_any_listed_role():
    dependency = require_role("admin", "agent_builder", "user")

    for role in ("admin", "agent_builder", "user"):
        assert (await dependency(user(role))).role == role
