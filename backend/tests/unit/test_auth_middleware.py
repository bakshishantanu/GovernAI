import jwt
import pytest
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.domain.auth.middleware import (
    DEV_TOKEN,
    get_current_user,
    get_supabase_jwt_secret,
)

# 32+ bytes, so PyJWT does not warn about a short HMAC key.
TEST_SECRET = "test-signing-secret-long-enough-for-hs256"


def creds(token: str) -> HTTPAuthorizationCredentials:
    """Stand in for FastAPI's Security injection."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def configured_secret(monkeypatch):
    """Give the middleware a signing secret, as a deployed server would have."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    return TEST_SECRET


@pytest.fixture
def dev_bypass_on(monkeypatch):
    monkeypatch.setenv("AUTH_ALLOW_DEV_TOKEN", "true")


@pytest.fixture(autouse=True)
def dev_bypass_off_by_default(monkeypatch):
    """Every test starts with the bypass off unless it asks for it."""
    monkeypatch.delenv("AUTH_ALLOW_DEV_TOKEN", raising=False)


@pytest.mark.asyncio
async def test_valid_token(configured_secret):
    user_id = str(uuid4())
    org_id = str(uuid4())

    payload = {"sub": user_id, "app_metadata": {"role": "admin", "org_id": org_id}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert str(user.org_id) == org_id
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_missing_sub_rejects(configured_secret):
    payload = {"app_metadata": {"role": "member"}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(token))

    assert exc.value.status_code == 401
    assert "missing subject" in exc.value.detail


@pytest.mark.asyncio
async def test_invalid_signature_rejects(configured_secret):
    payload = {"sub": str(uuid4())}
    token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(token))

    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail


# --- security regressions: these are the reason the bypass was gated ---


@pytest.mark.asyncio
async def test_dev_token_rejected_when_bypass_is_off(configured_secret):
    """The default posture. Without the flag, the dev token is just a bad token."""
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(DEV_TOKEN))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_dev_token_grants_admin_only_when_bypass_is_on(dev_bypass_on):
    """Local development still works, and needs no secret configured."""
    user = await get_current_user(creds(DEV_TOKEN))

    assert user.role == "admin"


def test_missing_secret_fails_closed(monkeypatch):
    """No signing secret must mean no logins, never a guessable default."""
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        "app.domain.auth.middleware.settings.SUPABASE_JWT_SECRET", "", raising=False
    )

    with pytest.raises(HTTPException) as exc:
        get_supabase_jwt_secret()

    assert exc.value.status_code == 503
