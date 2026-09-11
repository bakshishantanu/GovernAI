import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.auth import middleware as auth_middleware
from app.domain.auth.middleware import get_current_user
from app.domain.auth.models import Profile
from app.domain.auth.rbac import require_admin
from scripts.promote_to_admin import promote

TEST_SECRET = "test-signing-secret-long-enough-for-hs256"


def creds(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def configured_secret(monkeypatch):
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    return TEST_SECRET


@pytest.fixture
def dev_bypass_on(monkeypatch):
    monkeypatch.setenv("AUTH_ALLOW_DEV_TOKEN", "true")


@pytest.fixture(autouse=True)
def dev_bypass_off_by_default(monkeypatch):
    # "false", not deleted: the flag is also read from backend/.env, so an
    # explicit value keeps a developer's own .env from deciding these tests.
    monkeypatch.setenv("AUTH_ALLOW_DEV_TOKEN", "false")


@pytest.fixture(autouse=True)
def profile_roles(monkeypatch):
    """Stand-in for the `profiles` table, so get_current_user never reaches a
    real database. Maps user id -> role; empty means no one is promoted."""
    roles: dict = {}

    async def fake_profile_is_admin(user_id):
        return roles.get(user_id) == "admin"

    monkeypatch.setattr(auth_middleware, "profile_is_admin", fake_profile_is_admin)
    return roles


# 1. Admin Lockdown: Default role is always agent_builder, never admin
@pytest.mark.asyncio
async def test_jwt_default_role_is_agent_builder(configured_secret):
    payload = {"sub": str(uuid4())}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")
    user = await get_current_user(creds(token))
    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_jwt_unknown_role_defaults_to_agent_builder(configured_secret):
    payload = {"sub": str(uuid4()), "app_metadata": {"role": "hacker"}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")
    user = await get_current_user(creds(token))
    assert user.role == "agent_builder"


# 2. Dev token: dummy-token-user is supported when dev bypass is on, rejected when off
@pytest.mark.asyncio
async def test_dummy_token_user_is_agent_builder_when_bypass_on(dev_bypass_on):
    """The "dummy-token-user" name is kept so old dev sessions keep working,
    but the role it grants is agent_builder -- "user" is retired (D-057)."""
    user = await get_current_user(creds("dummy-token-user"))
    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_dummy_token_user_rejected_when_bypass_off():
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds("dummy-token-user"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_dummy_token_builder_is_agent_builder(dev_bypass_on):
    user = await get_current_user(creds("dummy-token-builder"))
    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_dummy_token_admin_is_admin(dev_bypass_on):
    user = await get_current_user(creds("dummy-token-admin"))
    assert user.role == "admin"


# 3. require_admin blocks agent_builder
@pytest.mark.asyncio
async def test_require_admin_blocks_agent_builder():
    from app.api.schemas.auth import CurrentUser

    builder = CurrentUser(id=uuid4(), org_id=uuid4(), role="agent_builder")
    with pytest.raises(HTTPException) as exc:
        await require_admin(builder)
    assert exc.value.status_code == 403


# 4. CLI Promotion Script Test
@pytest.mark.asyncio
async def test_promote_script_updates_profile():
    target_id = uuid4()
    mock_profile = Profile(id=target_id, org_id=uuid4(), role="agent_builder")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_profile
    mock_session.execute.return_value = mock_result

    with patch("scripts.promote_to_admin.AsyncSessionLocal") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        await promote(target_id)

    assert mock_profile.role == "admin"
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_promote_script_idempotent_if_already_admin():
    target_id = uuid4()
    mock_profile = Profile(id=target_id, org_id=uuid4(), role="admin")

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_profile
    mock_session.execute.return_value = mock_result

    with patch("scripts.promote_to_admin.AsyncSessionLocal") as mock_session_maker:
        mock_session_maker.return_value.__aenter__.return_value = mock_session
        await promote(target_id)

    assert mock_profile.role == "admin"
    mock_session.commit.assert_not_awaited()


# 5. A promoted admin is actually an admin (option (b)).
@pytest.mark.asyncio
async def test_promoted_profile_is_admin_without_being_on_the_email_list(
    configured_secret, profile_roles
):
    """promote_to_admin.py is the supported way to make an admin, and it works
    by setting profiles.role. That row must be honoured even though the email
    is on no list -- otherwise the script reports SUCCESS and changes nothing."""
    user_id = uuid4()
    token = jwt.encode(
        {"sub": str(user_id), "email": "promoted@company.com"},
        configured_secret,
        algorithm="HS256",
    )
    assert (await get_current_user(creds(token))).role == "agent_builder"

    profile_roles[user_id] = "admin"

    assert (await get_current_user(creds(token))).role == "admin"
