from __future__ import annotations
import os
import jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.schemas.auth import CurrentUser
from app.config import settings
from uuid import UUID

security = HTTPBearer()

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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> CurrentUser:
    """
    FastAPI dependency to validate the Supabase JWT and return the CurrentUser.
    """
    token = credentials.credentials

    # --- LOCAL DEV BYPASS (inert unless AUTH_ALLOW_DEV_TOKEN is set) ---
    if token == DEV_TOKEN:
        if not dev_token_allowed():
            raise HTTPException(status_code=401, detail="Invalid token")
        return CurrentUser(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            org_id=UUID("00000000-0000-0000-0000-000000000000"),
            role="admin"
        )

    secret = get_supabase_jwt_secret()

    try:
        # Decode the JWT token using the Supabase JWT secret
        # Supabase uses HS256 by default.
        # audience is usually "authenticated"
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"verify_aud": False}  # Adjust based on exact Supabase config
        )
        
        # Extract user identity from the subject claim
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(status_code=401, detail="Invalid token: missing subject")
        
        user_id = UUID(user_id_str)

        # Extract role and org_id from app_metadata (as specified in FRD)
        app_metadata = payload.get("app_metadata", {})
        
        # Default to "member" if not specified
        role = app_metadata.get("role", "member")
        if role not in ["admin", "member"]:
            role = "member"

        # Default org_id for MVP (single tenant)
        org_id_str = app_metadata.get("org_id")
        # If org_id is not yet embedded in the JWT by Supabase triggers,
        # we provide a fallback dummy UUID for local development/MVP to avoid crashing.
        if org_id_str:
            org_id = UUID(org_id_str)
        else:
            org_id = UUID("00000000-0000-0000-0000-000000000000")

        return CurrentUser(
            id=user_id,
            org_id=org_id,
            role=role
        )

    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
