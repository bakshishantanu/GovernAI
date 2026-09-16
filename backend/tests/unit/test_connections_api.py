from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.schemas.connection import SaveConnectionRequest
from app.api.v1.connections import delete_connection, list_connections, save_connection
from app.domain.connections.models import ConnectionModel


@pytest.fixture
def current_user():
    return CurrentUser(id=uuid.uuid4(), org_id=uuid.uuid4(), role="agent_builder")


@pytest.mark.asyncio
async def test_list_connections_returns_service_result(current_user):
    service = AsyncMock()
    connection = ConnectionModel(
        id=uuid.uuid4(), org_id=current_user.org_id, requirement_key="jira",
        type="credentials", label="Jira account", status="CONNECTED", preview={"email": "a@b.com"},
    )
    service.list_connections.return_value = [connection]

    envelope = await list_connections(user=current_user, service=service)

    service.list_connections.assert_awaited_once_with(current_user.org_id)
    assert envelope.data[0].requirement_key == "jira"


@pytest.mark.asyncio
async def test_save_connection_commits_and_returns_it(current_user):
    service = AsyncMock()
    saved = ConnectionModel(
        id=uuid.uuid4(), org_id=current_user.org_id, requirement_key="jira",
        type="credentials", label="Jira account", status="CONNECTED", preview={},
    )
    service.save_connection.return_value = saved
    db = AsyncMock()

    envelope = await save_connection(
        requirement_key="jira",
        payload=SaveConnectionRequest(
            type="credentials", label="Jira account", fields={"api_token": "x"}
        ),
        user=current_user,
        db=db,
        service=service,
    )

    db.commit.assert_awaited_once()
    assert envelope.data.requirement_key == "jira"


@pytest.mark.asyncio
async def test_delete_connection_404s_when_nothing_deleted(current_user):
    service = AsyncMock()
    service.delete_connection.return_value = False
    db = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await delete_connection(
            requirement_key="jira", user=current_user, db=db, service=service
        )
    assert exc.value.status_code == 404
