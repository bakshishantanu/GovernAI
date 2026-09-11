from uuid import uuid4

import pytest

from app.domain.agent_requests.service import (
    AgentRequestService,
    RequestAlreadyClaimedError,
)


class MockRepo:
    def __init__(self):
        self.requests = {}

    async def get_request(self, request_id):
        return self.requests.get(request_id)

    async def create_request(self, request):
        self.requests[request.id] = request
        return request

    async def claim_request(self, request_id, builder_id):
        req = self.requests.get(request_id)
        if req and req.status == "PENDING":
            req.status = "CLAIMED"
            req.builder_id = builder_id
            return True
        return False

    async def flush(self):
        pass


class MockEventBus:
    def publish(self, event):
        pass


@pytest.fixture
def request_service():
    return AgentRequestService(MockRepo(), MockEventBus())


@pytest.mark.asyncio
async def test_create_request(request_service):
    org_id = uuid4()
    user_id = uuid4()
    req = await request_service.create_request(
        org_id, user_id, "Test title", "Test description", ["skill_1"]
    )
    assert req.status == "PENDING"
    assert req.title == "Test title"
    assert req.requested_skills == ["skill_1"]


@pytest.mark.asyncio
async def test_claim_request(request_service):
    req = await request_service.create_request(uuid4(), uuid4(), "Test title", "Test desc", [])
    builder_id = uuid4()
    claimed = await request_service.claim_request(req.id, builder_id)
    assert claimed.status == "CLAIMED"
    assert claimed.builder_id == builder_id


@pytest.mark.asyncio
async def test_double_claim_fails(request_service):
    req = await request_service.create_request(uuid4(), uuid4(), "Test title", "Test desc", [])
    await request_service.claim_request(req.id, uuid4())

    with pytest.raises(RequestAlreadyClaimedError):
        await request_service.claim_request(req.id, uuid4())


@pytest.mark.asyncio
async def test_fulfill_request(request_service):
    req = await request_service.create_request(uuid4(), uuid4(), "Test title", "Test desc", [])
    await request_service.claim_request(req.id, uuid4())

    agent_id = uuid4()
    fulfilled = await request_service.fulfill_request(req.id, agent_id)
    assert fulfilled.status == "FULFILLED"
    assert fulfilled.agent_id == agent_id


@pytest.mark.asyncio
async def test_cancel_request(request_service):
    req = await request_service.create_request(uuid4(), uuid4(), "Test title", "Test desc", [])
    cancelled = await request_service.cancel_request(req.id)
    assert cancelled.status == "CANCELLED"
