from __future__ import annotations

import os
from uuid import UUID

import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient, PyJWKClientError

from app.api.schemas.auth import CurrentUser
from app.config import settings
from app.domain.auth.role_rules import role_for_email

security = HTTPBearer()

#: Lazily built, then reused — see get_jwks_client below.
_jwks_client: PyJWKClient | None = None


# The literal token that unlocks the local-development bypass below.
DEV_TOKEN = "dummy-token"

DEV_TOKENS = {
    DEV_TOKEN: ("admin", UUID("11111111-1111-1111-1111-111111111111")),
    "dummy-token-admin": ("admin", UUID("11111111-1111-1111-1111-111111111111")),
    "dummy-token-builder": ("agent_builder", UUID("22222222-2222-2222-2222-222222222222")),
    # "dummy-token-user" kept as an alias so old dev sessions and test
    # fixtures keep working; "user" itself is retired (D-057).
    "dummy-token-user": ("agent_builder", UUID("22222222-2222-2222-2222-222222222222")),
}

_jwks_client: PyJWKClient | None = None


def dev_token_allowed() -> bool:
    """Whether the local-development token bypass is switched on.

    Off unless AUTH_ALLOW_DEV_TOKEN is set explicitly, so the bypass can never
    be active in a deployed environment by accident.

    A real environment variable wins, including an explicit "false"; otherwise
    backend/.env decides, via settings. Reading os.environ alone silently
    ignored the .env line, because pydantic-settings loads .env into
    `settings` without exporting it.
    """
    raw = os.environ.get("AUTH_ALLOW_DEV_TOKEN")
    if raw is not None:
        return raw.strip().lower() in {"1", "true", "yes"}
    return settings.AUTH_ALLOW_DEV_TOKEN


def get_supabase_jwt_secret() -> str:
    """Return the Supabase JWT signing secret."""
    secret = os.environ.get("SUPABASE_JWT_SECRET") or settings.SUPABASE_JWT_SECRET
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this server",
        )
    return secret


def get_jwks_client() -> PyJWKClient | None:
    """Return a cached PyJWKClient pointing to the Supabase JWKS endpoint."""
    global _jwks_client
    supabase_url = os.environ.get("SUPABASE_URL") or settings.SUPABASE_URL
    if not supabase_url:
        return None
    if _jwks_client is None:
        jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwks_client


def decode_supabase_token(token: str) -> dict:
    """Decode and verify a Supabase JWT token.

    Supports:
    - JWKS-first asymmetric verification (ES256 / RS256) for modern Supabase.
    - HS256 symmetric verification fallback (when SUPABASE_JWT_SECRET is set).
    """
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token header: {str(e)}")

    alg = header.get("alg")
    last_error: Exception | None = None

    # 1. Asymmetric verification via JWKS (ES256 / RS256)
    if alg in ("ES256", "RS256") or "kid" in header:
        jwks_client = get_jwks_client()
        if jwks_client:
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
                return jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=[alg] if alg else ["ES256", "RS256"],
                    options={"verify_aud": False},
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except (jwt.InvalidTokenError, PyJWKClientError) as e:
                last_error = e
            except Exception as e:
                last_error = e
        else:
            last_error = Exception("JWKS client not configured (missing SUPABASE_URL)")

    # 2. Symmetric verification fallback via SUPABASE_JWT_SECRET (HS256)
    secret = os.environ.get("SUPABASE_JWT_SECRET") or settings.SUPABASE_JWT_SECRET
    if secret:
        try:
            return jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidTokenError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")

    if last_error is not None:
        raise HTTPException(
            status_code=401, detail=f"Could not validate credentials: {str(last_error)}"
        )

    raise HTTPException(
        status_code=503,
        detail="Authentication is not configured on this server",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> CurrentUser:
    """
    FastAPI dependency to validate the Supabase JWT and return the CurrentUser.
    """
    token = credentials.credentials

    # --- LOCAL DEV BYPASS (inert unless AUTH_ALLOW_DEV_TOKEN is set) ---
    if token in DEV_TOKENS:
        if not dev_token_allowed():
            raise HTTPException(status_code=401, detail="Invalid token")
        dev_role, user_id = DEV_TOKENS[token]
        return CurrentUser(
            id=user_id,
            org_id=UUID("00000000-0000-0000-0000-000000000000"),
            role=dev_role,  # type: ignore[arg-type]
            email=None,
            full_name=None,
        )

    payload = decode_supabase_token(token)

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=401, detail="Invalid token: missing subject")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token: malformed subject UUID")

    email = payload.get("email")
    user_metadata = payload.get("user_metadata", {})
    full_name = user_metadata.get("full_name") or payload.get("name")
    app_metadata = payload.get("app_metadata", {})

    # Role is decided by email, not by app_metadata.role - that field is
    # arbitrary claim data a project admin sets by hand, with nothing in
    # this codebase keeping it in sync with who someone actually is.
    # role_for_email is the one source of truth (see role_rules.py); an
    # unlisted email always gets "agent_builder", never something higher.
    role = role_for_email(email)

    org_id_str = app_metadata.get("org_id")
    if org_id_str:
        try:
            org_id = UUID(org_id_str)
        except ValueError:
            org_id = UUID("00000000-0000-0000-0000-000000000000")
    else:
        org_id = UUID("00000000-0000-0000-0000-000000000000")

    return CurrentUser(
        id=user_id,
        org_id=org_id,
        role=role,
        email=email,
        full_name=full_name,
    )
