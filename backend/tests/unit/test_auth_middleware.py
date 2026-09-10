from uuid import uuid4

import jwt
import pytest
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
    payload = {"app_metadata": {"role": "agent_builder"}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(token))

    assert exc.value.status_code == 401
    assert "missing subject" in exc.value.detail


@pytest.mark.asyncio
async def test_user_role_preserved_and_has_builder_permissions(configured_secret):
    user_id = str(uuid4())
    org_id = str(uuid4())
    payload = {"sub": user_id, "app_metadata": {"role": "user", "org_id": org_id}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "user"
    assert user.is_builder is True


@pytest.mark.asyncio
async def test_default_role_is_agent_builder(configured_secret):
    user_id = str(uuid4())
    payload = {"sub": user_id}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "agent_builder"


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


@pytest.mark.asyncio
async def test_admin_email_allowlist_promotes_to_admin(configured_secret, monkeypatch):
    """Users whose email matches ADMIN_EMAILS are resolved as admin even with builder metadata."""
    monkeypatch.setenv("ADMIN_EMAILS", "boss@governai.com, admin@deloitte.com")
    user_id = str(uuid4())
    payload = {
        "sub": user_id,
        "email": "Boss@GovernAI.com",
        "app_metadata": {"role": "agent_builder"},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "admin"
    assert user.is_admin is True
    assert user.email == "Boss@GovernAI.com"


@pytest.mark.asyncio
async def test_dummy_token_user_grants_user_role(dev_bypass_on):
    """dummy-token-user grants role='user' with non-admin builder permissions."""
    user = await get_current_user(creds("dummy-token-user"))

    assert user.role == "user"
    assert user.is_builder is True
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_jwks_asymmetric_token_decoding(monkeypatch):
    """Verify ES256/RS256 tokens decoded via JWKS signing key without requiring secret."""
    from unittest.mock import MagicMock
    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate a throwaway RSA private key for testing asymmetric signing
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    user_id = str(uuid4())
    payload = {"sub": user_id, "email": "engineer@company.com", "app_metadata": {"role": "agent_builder"}}
    token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})

    mock_jwks_client = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    monkeypatch.setattr("app.domain.auth.middleware.get_jwks_client", lambda: mock_jwks_client)
    # Ensure SUPABASE_JWT_SECRET is unset to guarantee asymmetric path was used
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr("app.domain.auth.middleware.settings.SUPABASE_JWT_SECRET", "", raising=False)

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "agent_builder"
    assert user.email == "engineer@company.com"

