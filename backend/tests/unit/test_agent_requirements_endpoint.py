from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.schemas.auth import CurrentUser
from app.api.v1.agents import get_agent_requirements
from app.domain.agents.models import Agent


@pytest.fixture
def current_user():
    return CurrentUser(id=uuid.uuid4(), org_id=uuid.uuid4(), role="agent_builder")


def _service_with(agent):
    service = MagicMock()
    service.agent_repo = MagicMock()
    service.agent_repo.get_agent = AsyncMock(return_value=agent)
    service.agent_repo.list_skill_ids = AsyncMock(return_value=["ticketing"])
    service.skill_repo = MagicMock()
    return service


@pytest.mark.asyncio
async def test_get_agent_requirements_404s_for_another_orgs_agent(current_user):
    agent = Agent(
        id=uuid.uuid4(), org_id=uuid.uuid4(), owner_id=uuid.uuid4(), name="a", description="d"
    )
    service = _service_with(agent)

    with pytest.raises(HTTPException) as exc:
        await get_agent_requirements(
            agent_id=agent.id, user=current_user, db=AsyncMock(), service=service
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_agent_requirements_returns_resolved_statuses(current_user):
    agent = Agent(
        id=uuid.uuid4(), org_id=current_user.org_id, owner_id=uuid.uuid4(), name="a", description="d"
    )
    service = _service_with(agent)

    status = MagicMock(
        key="jira", type="credentials", label="Jira account", description="", fields=[],
        satisfied=False,
    )
    with patch(
        "app.api.v1.agents.resolve_requirements",
        new=AsyncMock(return_value=[status]),
    ):
        envelope = await get_agent_requirements(
            agent_id=agent.id, user=current_user, db=AsyncMock(), service=service
        )

    assert envelope.data[0].key == "jira"
    assert envelope.data[0].satisfied is False
