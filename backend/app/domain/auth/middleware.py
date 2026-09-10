from __future__ import annotations

import os
from uuid import UUID

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.api.schemas.auth import CurrentUser
from app.config import settings
from app.domain.auth.role_rules import role_for_email

security = HTTPBearer()

#: Lazily built, then reused — PyJWKClient caches the fetched keyset itself
#: (`cache_keys=True`), so this only hits Supabase's JWKS endpoint once per
#: process, not once per request.
_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        jwks_url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


# The literal token that unlocks the local-development bypass below.
DEV_TOKEN = "dummy-token"


def dev_token_allowed() -> bool:
    """Whether the local-development token bypass is switched on.

    Off unless AUTH_ALLOW_DEV_TOKEN is set explicitly, so the bypass can never
    be active in a deployed environment by accident.
    """
    return os.environ.get("AUTH_ALLOW_DEV_TOKEN", "").strip().lower() in {"1", "true", "yes"}


def get_supabase_jwt_secret() -> str:
    """Return the Supabase JWT signing secret.

    Fails closed when it is not configured: without the real secret we cannot
    verify a signature, and falling back to a known default would let anyone
    forge a valid token.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET") or settings.SUPABASE_JWT_SECRET
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this server",
        )
    return secret


def _decode_supabase_jwt(token: str) -> dict:
    """Verify and decode a real Supabase-issued access token.

    Supabase signs tokens one of two ways depending on the project's Auth
    settings, and this backend must handle either without knowing in advance
    which one a given project uses:

    - **Asymmetric signing keys** (ES256/RS256, Supabase's current default
      for new projects) — verified against the project's own JWKS endpoint
      (`/auth/v1/.well-known/jwks.json`), keyed by the token's own `kid`
      header. This is the path a real project like this one's actually
      takes; confirmed live by decoding a real signed-in session's token and
      finding `alg: ES256` with a `kid` that matches a key the JWKS endpoint
      actually serves.
    - **Legacy shared-secret signing** (HS256, older projects / the
      `SUPABASE_JWT_SECRET` this codebase already had a path for) — tried
      only as a fallback, since it needs no network call and costs nothing
      to attempt after the JWKS lookup can't place the token's `kid`.

    Raises the same `jwt` exceptions either path would — callers already
    handle `ExpiredSignatureError`/`InvalidTokenError` uniformly.
    """
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            options={"verify_aud": False},
        )
    except jwt.PyJWKClientError:
        # No key in the project's JWKS matched this token's `kid` (or it has
        # none) — not necessarily invalid, just possibly an older-style
        # HS256 token. Fall back to the shared-secret path; a token that is
        # genuinely bad will still fail there with its own real error.
        secret = get_supabase_jwt_secret()
        return jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> CurrentUser:
    """
    FastAPI dependency to validate the Supabase JWT and return the CurrentUser.
    """
    token = credentials.credentials

    # --- LOCAL DEV BYPASS (inert unless AUTH_ALLOW_DEV_TOKEN is set) ---
    # Both "dummy-token-builder" and "dummy-token-user" stay accepted (not
    # just silently dropped) so an old bookmarked dev session / test fixture
    # from either the three-role era or this session's own earlier "user"
    # naming keeps working -- both now resolve to the same "agent_builder"
    # role and id (D-057: standardized on "agent_builder" over "user").
    if token in (DEV_TOKEN, "dummy-token-admin", "dummy-token-builder", "dummy-token-user"):
        if not dev_token_allowed():
            raise HTTPException(status_code=401, detail="Invalid token")
        dev_role = "admin"
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        if token in ("dummy-token-builder", "dummy-token-user"):
            dev_role = "agent_builder"
            user_id = UUID("33333333-3333-3333-3333-333333333333")
        return CurrentUser(
            id=user_id,
            org_id=UUID("00000000-0000-0000-0000-000000000000"),
            role=dev_role,  # type: ignore[arg-type]
        )

    try:
        payload = _decode_supabase_jwt(token)

        # Extract user identity from the subject claim
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")

        user_id = UUID(user_id_str)

        # Role is decided by email, not by app_metadata.role - that field is
        # arbitrary claim data a project admin sets by hand, with nothing in
        # this codebase keeping it in sync with who someone actually is.
        # role_for_email is the one source of truth (see role_rules.py); an
        # unlisted email always gets "agent_builder", never something higher.
        role = role_for_email(payload.get("email"))

        # Default org_id for MVP (single tenant)
        app_metadata = payload.get("app_metadata", {})
        org_id_str = app_metadata.get("org_id")
        # If org_id is not yet embedded in the JWT by Supabase triggers,
        # we provide a fallback dummy UUID for local development/MVP to avoid crashing.
        if org_id_str:
            org_id = UUID(org_id_str)
        else:
            org_id = UUID("00000000-0000-0000-0000-000000000000")

        # The real display identity, straight from Supabase's own claims —
        # never fabricated. `full_name` lives under `user_metadata` (what the
        # signup form set, or an OAuth provider's own profile data), not
        # `app_metadata` (which is admin-set config, the same reason role is
        # never read from there either).
        email = payload.get("email")
        full_name = (payload.get("user_metadata") or {}).get("full_name")

        return CurrentUser(
            id=user_id, org_id=org_id, role=role, email=email, full_name=full_name
        )

    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
