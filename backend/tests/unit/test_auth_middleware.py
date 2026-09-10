from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
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

    payload = {
        "sub": user_id,
        "email": "admin@governai.com",
        "app_metadata": {"org_id": org_id},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert str(user.org_id) == org_id
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_email_and_full_name_come_from_the_real_token_not_invented(configured_secret):
    """The sidebar/settings identity bug: CurrentUser must carry the real
    Supabase claims so the UI can show a real name instead of the literal
    role string — and must not invent one when the claim is absent."""
    payload = {
        "sub": str(uuid4()),
        "email": "pladha612@gmail.com",
        "user_metadata": {"full_name": "Pranav Ladha"},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.email == "pladha612@gmail.com"
    assert user.full_name == "Pranav Ladha"


@pytest.mark.asyncio
async def test_dev_token_carries_no_invented_identity(dev_bypass_on):
    """The dev bypass has no real person behind it — email/full_name must
    stay null, not a fabricated placeholder."""
    user = await get_current_user(creds(DEV_TOKEN))

    assert user.email is None
    assert user.full_name is None


@pytest.mark.asyncio
async def test_role_comes_from_email_not_app_metadata(configured_secret):
    """app_metadata.role is arbitrary claim data - it must never grant a role."""
    payload = {
        "sub": str(uuid4()),
        "email": "nobody-special@example.com",
        # A forged/misconfigured claim asking for admin must not work.
        "app_metadata": {"role": "admin"},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_an_unlisted_email_gets_agent_builder_not_a_third_role(configured_secret):
    """Two roles only: anyone not on the admin list gets "agent_builder" —
    there is no third role left to grant (D-057: standardized on this name
    over "user" since it's the one with real accounts on it)."""
    payload = {"sub": str(uuid4()), "email": "builder@governai.com"}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_token_with_no_email_defaults_to_agent_builder(configured_secret):
    payload = {"sub": str(uuid4())}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "agent_builder"


@pytest.mark.asyncio
async def test_missing_sub_rejects(configured_secret):
    payload = {"app_metadata": {"role": "agent_builder"}}
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


# --- real-world regression: Supabase's asymmetric (ES256) signing keys ---
#
# Found live 2026-09-10: a genuinely signed-in real account's every API call
# was failing with "Invalid token: The specified alg value is not allowed",
# because this Supabase project signs access tokens with ES256 (its current
# default for new projects, verified against a real JWKS endpoint), while
# this middleware only ever tried HS256 against a shared secret. These tests
# pin the fix (`_decode_supabase_jwt`'s JWKS-first, HS256-fallback path)
# against a real EC keypair and a mocked JWKS client, so this exact failure
# mode cannot silently return.


@pytest.fixture
def es256_keypair():
    private_key = ec.generate_private_key(ec.SECP256R1())
    return private_key, private_key.public_key()


@pytest.fixture
def mock_jwks_client(monkeypatch, es256_keypair):
    """Stands in for a real call to Supabase's JWKS endpoint, returning this
    test's own EC public key instead of hitting the network."""
    _, public_key = es256_keypair

    class _FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(
        "app.domain.auth.middleware._get_jwks_client", lambda: _FakeJWKClient()
    )


@pytest.mark.asyncio
async def test_es256_token_verified_against_jwks(mock_jwks_client, es256_keypair):
    """The actual bug: a real Supabase session's ES256-signed token must
    authenticate, not 401 with 'alg value is not allowed'."""
    private_key, _ = es256_keypair
    user_id = str(uuid4())
    payload = {"sub": user_id, "email": "admin@governai.com"}
    token = jwt.encode(payload, private_key, algorithm="ES256", headers={"kid": "test-kid"})

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "admin"


@pytest.mark.asyncio
async def test_es256_token_with_wrong_key_rejected(mock_jwks_client):
    """A token signed by a *different* private key than the one the (mocked)
    JWKS endpoint serves must still be rejected -- the fallback to HS256
    must not accidentally accept it under the wrong algorithm either."""
    other_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        {"sub": str(uuid4())}, other_key, algorithm="ES256", headers={"kid": "test-kid"}
    )

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(token))

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_hs256_token_still_works_when_jwks_has_no_matching_key(
    configured_secret, monkeypatch
):
    """Legacy HS256-signed tokens (an older Supabase project, or this
    project's own dev-signed test tokens) must keep working via the fallback
    -- the JWKS lookup failing to place the token is not itself a rejection."""
    from jwt import PyJWKClientError

    class _FakeJWKClientNoMatch:
        def get_signing_key_from_jwt(self, token):
            raise PyJWKClientError("no matching key found")

    monkeypatch.setattr(
        "app.domain.auth.middleware._get_jwks_client", lambda: _FakeJWKClientNoMatch()
    )

    payload = {"sub": str(uuid4()), "email": "admin@governai.com"}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "admin"
