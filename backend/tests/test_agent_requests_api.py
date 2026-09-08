import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest
from fastapi import HTTPException
from app.api.v1.agent_requests import (
    create_request,
    list_requests,
    get_request,
    claim_request,
    cancel_request,
)
from app.api.schemas.agent_requests import AgentRequestCreate
from app.api.schemas.auth import CurrentUser
from app.domain.agent_requests.models import AgentRequest
from app.domain.agent_requests.service import (
    AgentRequestService,
    RequestAlreadyClaimedError,
    RequestNotFoundError,
)

@pytest.fixture
def org_id():
    return uuid.uuid4()

@pytest.fixture
def user_client(org_id):
    return CurrentUser(
        id=uuid.uuid4(),
        org_id=org_id,
        role="user",
    )

@pytest.fixture
def builder_client(org_id):
    return CurrentUser(
        id=uuid.uuid4(),
        org_id=org_id,
        role="agent_builder",
    )

@pytest.fixture
def admin_client(org_id):
    return CurrentUser(
        id=uuid.uuid4(),
        org_id=org_id,
        role="admin",
    )

@pytest.mark.asyncio
async def test_create_request_endpoint(user_client):
    service = AsyncMock(spec=AgentRequestService)
    service.create_request.return_value = AgentRequest(
        id=uuid.uuid4(),
        org_id=user_client.org_id,
        requester_id=user_client.id,
        title="Test Agent Request",
        description="A test request",
        requested_skills=["ticketing"],
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    payload = AgentRequestCreate(
        title="Test Agent Request",
        description="A test request",
        requested_skills=["ticketing"],
    )

    resp = await create_request(request=payload, service=service, user=user_client)
    assert resp.title == "Test Agent Request"
    assert resp.status == "PENDING"
    assert resp.requester_id == user_client.id
    service.create_request.assert_awaited_once_with(
        org_id=user_client.org_id,
        requester_id=user_client.id,
        title="Test Agent Request",
        description="A test request",
        requested_skills=["ticketing"],
    )

@pytest.mark.asyncio
async def test_list_requests_scopes_to_user(user_client):
    service = AsyncMock(spec=AgentRequestService)
    service.request_repo = AsyncMock()
    service.request_repo.list_requests.return_value = []

    await list_requests(service=service, user=user_client)

    # Asserts that requester_id is forced to user.id for user role
    service.request_repo.list_requests.assert_awaited_once_with(
        org_id=user_client.org_id,
        requester_id=user_client.id,
        builder_id=None,
        status=None,
    )

@pytest.mark.asyncio
async def test_get_request_detail_forbidden_for_different_user(org_id):
    owner_id = uuid.uuid4()
    other_user = CurrentUser(id=uuid.uuid4(), org_id=org_id, role="user")

    service = AsyncMock(spec=AgentRequestService)
    service.request_repo = AsyncMock()
    service.request_repo.get_request.return_value = AgentRequest(
        id=uuid.uuid4(),
        org_id=org_id,
        requester_id=owner_id,
        title="Secret Request",
        description="Private",
        requested_skills=[],
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with pytest.raises(HTTPException) as exc:
        await get_request(request_id=uuid.uuid4(), service=service, user=other_user)

    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_claim_request_success(builder_client):
    req_id = uuid.uuid4()
    service = AsyncMock(spec=AgentRequestService)
    service.request_repo = AsyncMock()
    service.request_repo.get_request.return_value = AgentRequest(
        id=req_id,
        org_id=builder_client.org_id,
        requester_id=uuid.uuid4(),
        title="Claimable",
        description="...",
        requested_skills=[],
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service.claim_request.return_value = AgentRequest(
        id=req_id,
        org_id=builder_client.org_id,
        requester_id=uuid.uuid4(),
        builder_id=builder_client.id,
        title="Claimable",
        description="...",
        requested_skills=[],
        status="CLAIMED",
        claimed_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    res = await claim_request(request_id=req_id, service=service, user=builder_client)
    assert res.status == "CLAIMED"
    assert res.builder_id == builder_client.id

@pytest.mark.asyncio
async def test_claim_request_conflict(builder_client):
    req_id = uuid.uuid4()
    service = AsyncMock(spec=AgentRequestService)
    service.request_repo = AsyncMock()
    service.request_repo.get_request.return_value = AgentRequest(
        id=req_id,
        org_id=builder_client.org_id,
        requester_id=uuid.uuid4(),
        title="Already claimed",
        description="...",
        requested_skills=[],
        status="CLAIMED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service.claim_request.side_effect = RequestAlreadyClaimedError("Already claimed")

    with pytest.raises(HTTPException) as exc:
        await claim_request(request_id=req_id, service=service, user=builder_client)

    assert exc.value.status_code == 409

@pytest.mark.asyncio
async def test_cancel_request_by_owner(user_client):
    req_id = uuid.uuid4()
    service = AsyncMock(spec=AgentRequestService)
    service.request_repo = AsyncMock()
    service.request_repo.get_request.return_value = AgentRequest(
        id=req_id,
        org_id=user_client.org_id,
        requester_id=user_client.id,
        title="To cancel",
        description="...",
        requested_skills=[],
        status="PENDING",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    service.cancel_request.return_value = AgentRequest(
        id=req_id,
        org_id=user_client.org_id,
        requester_id=user_client.id,
        title="To cancel",
        description="...",
        requested_skills=[],
        status="CANCELLED",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    res = await cancel_request(request_id=req_id, service=service, user=user_client)
    assert res.status == "CANCELLED"
