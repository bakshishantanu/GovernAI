from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.config import Settings, settings
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
    """Every test starts with the bypass off unless it asks for it.

    Set to "false" rather than deleted: the flag is also read from backend/.env
    (via settings), so deleting the variable would let a developer's own .env
    decide the outcome of these tests. An explicit environment value wins.
    """
    monkeypatch.setenv("AUTH_ALLOW_DEV_TOKEN", "false")


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
async def test_app_metadata_role_cannot_promote(configured_secret):
    """The escalation this model closes: `app_metadata.role` is hand-set
    config a project admin edits in the Supabase dashboard, with nothing
    keeping it in sync with who someone is. It used to be able to make
    someone an admin. Email decides now, and an unlisted email stays
    agent_builder no matter what the token claims."""
    payload = {
        "sub": str(uuid4()),
        "email": "outsider@example.com",
        "app_metadata": {"role": "admin"},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "agent_builder"
    assert user.is_admin is False


@pytest.mark.asyncio
async def test_missing_sub_rejects(configured_secret):
    payload = {"app_metadata": {"role": "agent_builder"}}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(token))

    assert exc.value.status_code == 401
    assert "missing subject" in exc.value.detail


@pytest.mark.asyncio
async def test_legacy_user_role_claim_resolves_to_agent_builder(configured_secret):
    """A token still carrying the retired "user" role name does not keep it:
    two roles only now, and the surviving name is agent_builder (D-057)."""
    user_id = str(uuid4())
    org_id = str(uuid4())
    payload = {
        "sub": user_id,
        "email": "someone@company.com",
        "app_metadata": {"role": "user", "org_id": org_id},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "agent_builder"
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


@pytest.mark.asyncio
async def test_dev_bypass_honours_dotenv_when_env_var_unset(monkeypatch):
    """AUTH_ALLOW_DEV_TOKEN=true in backend/.env must switch the bypass on.

    Regression: the flag was read from os.environ only, and pydantic-settings
    loads .env into `settings` without exporting it - so the .env line was
    silently ignored and every dev-token request was a 401.
    """
    monkeypatch.delenv("AUTH_ALLOW_DEV_TOKEN", raising=False)
    monkeypatch.setattr(settings, "AUTH_ALLOW_DEV_TOKEN", True)

    user = await get_current_user(creds(DEV_TOKEN))

    assert user.role == "admin"


@pytest.mark.asyncio
async def test_explicit_env_false_overrides_dotenv_true(configured_secret, monkeypatch):
    """A real environment variable still wins, so the bypass can be forced off."""
    monkeypatch.setenv("AUTH_ALLOW_DEV_TOKEN", "false")
    monkeypatch.setattr(settings, "AUTH_ALLOW_DEV_TOKEN", True)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds(DEV_TOKEN))

    assert exc.value.status_code == 401


def test_dev_bypass_defaults_off():
    """A server with neither .env line nor variable must never accept dev tokens."""
    assert Settings.model_fields["AUTH_ALLOW_DEV_TOKEN"].default is False


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
async def test_dummy_token_user_grants_builder_role(dev_bypass_on):
    """dummy-token-user is kept as an alias, but "user" itself is retired
    (D-057) -- it resolves to the surviving agent_builder role."""
    user = await get_current_user(creds("dummy-token-user"))

    assert user.role == "agent_builder"
    assert user.is_builder is True
    assert user.is_admin is False
    assert user.email is None
    assert user.full_name is None


@pytest.mark.asyncio
async def test_full_name_extracted_from_user_metadata(configured_secret):
    """User full_name is parsed from user_metadata claim."""
    user_id = str(uuid4())
    payload = {
        "sub": user_id,
        "email": "jane@company.com",
        "user_metadata": {"full_name": "Jane Doe"},
        "app_metadata": {"role": "agent_builder"},
    }
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.full_name == "Jane Doe"
    assert user.email == "jane@company.com"


@pytest.mark.asyncio
async def test_jwks_asymmetric_token_decoding(monkeypatch):
    """Verify ES256/RS256 tokens decoded via JWKS signing key without requiring secret."""
    from unittest.mock import MagicMock

    from cryptography.hazmat.primitives.asymmetric import rsa

    # Generate a throwaway RSA private key for testing asymmetric signing
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    user_id = str(uuid4())
    payload = {
        "sub": user_id,
        "email": "engineer@company.com",
        "app_metadata": {"role": "agent_builder"},
    }
    token = jwt.encode(payload, private_key, algorithm="RS256", headers={"kid": "test-key-id"})

    mock_jwks_client = MagicMock()
    mock_signing_key = MagicMock()
    mock_signing_key.key = public_key
    mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

    monkeypatch.setattr("app.domain.auth.middleware.get_jwks_client", lambda: mock_jwks_client)
    # Ensure SUPABASE_JWT_SECRET is unset to guarantee asymmetric path was used
    monkeypatch.delenv("SUPABASE_JWT_SECRET", raising=False)
    monkeypatch.setattr(
        "app.domain.auth.middleware.settings.SUPABASE_JWT_SECRET", "", raising=False
    )

    user = await get_current_user(creds(token))

    assert str(user.id) == user_id
    assert user.role == "agent_builder"
    assert user.email == "engineer@company.com"



# --- real-world regression: Supabase's asymmetric (ES256) signing keys ---
#
# Found live 2026-09-10: a genuinely signed-in real account's every API call
# was failing with "Invalid token: The specified alg value is not allowed",
# because this Supabase project signs access tokens with ES256 (its current
# default for new projects, verified against a real JWKS endpoint), while
# this middleware only ever tried HS256 against a shared secret. These tests
# pin the fix (`decode_supabase_token`'s JWKS-first, HS256-fallback path)
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
        "app.domain.auth.middleware.get_jwks_client", lambda: _FakeJWKClient()
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
        "app.domain.auth.middleware.get_jwks_client", lambda: _FakeJWKClientNoMatch()
    )

    payload = {"sub": str(uuid4()), "email": "admin@governai.com"}
    token = jwt.encode(payload, configured_secret, algorithm="HS256")

    user = await get_current_user(creds(token))

    assert user.role == "admin"
