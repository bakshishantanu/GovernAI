import jwt
import pytest
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from app.domain.auth.middleware import get_current_user, get_supabase_jwt_secret

@pytest.mark.asyncio
async def test_valid_token():
    secret = get_supabase_jwt_secret()
    user_id = str(uuid4())
    org_id = str(uuid4())
    
    # Create a mock Supabase JWT
    payload = {
        "sub": user_id,
        "app_metadata": {
            "role": "admin",
            "org_id": org_id
        }
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    
    # Mock the FastAPI Security injection
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    # Run the middleware
    user = await get_current_user(creds)
    
    assert str(user.id) == user_id
    assert str(user.org_id) == org_id
    assert user.role == "admin"

@pytest.mark.asyncio
async def test_missing_sub_rejects():
    secret = get_supabase_jwt_secret()
    payload = {"app_metadata": {"role": "member"}}
    token = jwt.encode(payload, secret, algorithm="HS256")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    
    assert exc.value.status_code == 401
    assert "missing subject" in exc.value.detail

@pytest.mark.asyncio
async def test_invalid_signature_rejects():
    payload = {"sub": str(uuid4())}
    token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    
    with pytest.raises(HTTPException) as exc:
        await get_current_user(creds)
    
    assert exc.value.status_code == 401
    assert "Invalid token" in exc.value.detail
