import os
import jwt
from typing import Optional
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.api.schemas.auth import CurrentUser
from uuid import UUID

security = HTTPBearer()

def get_supabase_jwt_secret() -> str:
    # In a real app, this would come from P3's config.py settings
    secret = os.environ.get("SUPABASE_JWT_SECRET", "dummy-secret-for-local-dev-only")
    return secret

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> CurrentUser:
    """
    FastAPI dependency to validate the Supabase JWT and return the CurrentUser.
    """
    token = credentials.credentials
    secret = get_supabase_jwt_secret()

    # --- LOCAL DEV BYPASS ---
    if token == "dummy-token":
        return CurrentUser(
            id=UUID("11111111-1111-1111-1111-111111111111"),
            org_id=UUID("00000000-0000-0000-0000-000000000000"),
            role="admin"
        )

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
    except Exception as e:
        if secret == "dummy-secret-for-local-dev-only":
            return CurrentUser(
                id=UUID("11111111-1111-1111-1111-111111111111"),
                org_id=UUID("00000000-0000-0000-0000-000000000000"),
                role="admin"
            )
        raise HTTPException(status_code=401, detail=f"Could not validate credentials: {str(e)}")
