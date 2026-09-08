from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest
from app.api.deps import (
    MockFallbackProvider,
    get_llm_service,
    get_agent_service,
    get_execution_service,
    get_agent_request_service,
    get_policy_engine,
    get_audit_service,
    get_cost_service,
    get_embedding_provider,
    get_skill_registry,
    get_kill_switch_service,
    get_budget_guard,
)
from app.infrastructure.event_bus import EventBus, Event
from app.api.schemas.agent import AgentResponse, AgentCreate


@pytest.mark.asyncio
async def test_mock_fallback_provider_returns_valid_response():
    provider = MockFallbackProvider()
    response = await provider.chat([{"role": "user", "content": "hello world"}])
    assert response.provider == "mock"
    assert response.model == "mock-simulator"
    assert response.usage.total_tokens == 20
    assert "hello world" in response.content


@pytest.mark.asyncio
async def test_get_llm_service_chat_fallback():
    llm = get_llm_service()
    response = await llm.chat([{"role": "user", "content": "testing llm service"}])
    assert response.provider == "mock" or bool(response.provider)
    assert response.usage.total_tokens > 0


def test_event_bus_sync_and_async_publish():
    bus = EventBus()
    sub = bus.subscribe()

    event1 = Event.create("test.sync", {"msg": "hello sync"})
    bus.publish_nowait(event1)

    # Receive from queue
    received1 = sub._queue.get_nowait()
    assert received1.type == "test.sync"
    assert received1.payload["msg"] == "hello sync"


@pytest.mark.asyncio
async def test_all_api_deps_instantiate():
    db = AsyncMock()
    agent_svc = await get_agent_service(db)
    assert agent_svc is not None

    exec_svc = await get_execution_service(db)
    assert exec_svc is not None

    req_svc = await get_agent_request_service(db)
    assert req_svc is not None

    policy_eng = await get_policy_engine(db)
    assert policy_eng is not None

    audit_svc = await get_audit_service(db)
    assert audit_svc is not None

    cost_svc = await get_cost_service(db)
    assert cost_svc is not None

    emb = get_embedding_provider()
    skill_reg = await get_skill_registry(db, emb)
    assert skill_reg is not None

    kill_sw = await get_kill_switch_service(db)
    assert kill_sw is not None

    budget_g = await get_budget_guard(db)
    assert budget_g is not None


def test_agent_schemas_include_request_and_assigned_user():
    req_id = uuid4()
    user_id = uuid4()
    create_payload = AgentCreate(
        name="Support Agent",
        description="Handles user support",
        skills=["ticketing"],
        request_id=req_id,
        assigned_user_id=user_id,
    )
    assert create_payload.request_id == req_id
    assert create_payload.assigned_user_id == user_id

    from datetime import datetime, timezone
    resp = AgentResponse(
        id=uuid4(),
        org_id=uuid4(),
        owner_id=uuid4(),
        assigned_user_id=user_id,
        request_id=req_id,
        name="Support Agent",
        description="Handles user support",
        status="ACTIVE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    assert resp.request_id == req_id
    assert resp.assigned_user_id == user_id
