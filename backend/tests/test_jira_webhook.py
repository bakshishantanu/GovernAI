from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.execution_runner import run_execution
from app.api.v1.webhooks import JiraIssueWebhook, jira_issue_created
from app.config import settings
from app.domain.agents.models import Agent, AgentPassport
from app.domain.executions.models import Execution


@pytest.fixture(autouse=True)
def webhook_secret(monkeypatch):
    monkeypatch.setattr(settings, "JIRA_WEBHOOK_SECRET", "test-secret")


def _active_agent(**overrides) -> Agent:
    agent = Agent(
        id=overrides.get("id", uuid.uuid4()),
        org_id=overrides.get("org_id", uuid.uuid4()),
        owner_id=uuid.uuid4(),
        name="Ticket Triage Bot",
        description="Reads and drafts replies to tickets",
        status="ACTIVE",
    )
    agent.passport = AgentPassport(
        id=uuid.uuid4(), agent=agent, compliance_status="APPROVED", lifecycle_state="ACTIVE"
    )
    return agent


@pytest.mark.asyncio
async def test_missing_secret_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await jira_issue_created(
            payload=JiraIssueWebhook(issue_key="SCRUM-1", summary="s", description="d"),
            background_tasks=BackgroundTasks(),
            x_webhook_secret=None,
            db=AsyncMock(),
            llm_service=AsyncMock(),
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_wrong_secret_is_rejected():
    with pytest.raises(HTTPException) as exc:
        await jira_issue_created(
            payload=JiraIssueWebhook(issue_key="SCRUM-1", summary="s", description="d"),
            background_tasks=BackgroundTasks(),
            x_webhook_secret="not-the-secret",
            db=AsyncMock(),
            llm_service=AsyncMock(),
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_unconfigured_secret_fails_closed(monkeypatch):
    """No JIRA_WEBHOOK_SECRET configured on the server -- refuse every call,
    rather than accepting requests nobody can actually be authorized for."""
    monkeypatch.setattr(settings, "JIRA_WEBHOOK_SECRET", "")

    with pytest.raises(HTTPException) as exc:
        await jira_issue_created(
            payload=JiraIssueWebhook(issue_key="SCRUM-1", summary="s", description="d"),
            background_tasks=BackgroundTasks(),
            x_webhook_secret="anything",
            db=AsyncMock(),
            llm_service=AsyncMock(),
        )
    assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_starts_a_run_for_every_active_agent_with_ticketing(monkeypatch):
    agent_a = _active_agent()
    agent_b = _active_agent()

    from app.api.v1 import webhooks as webhooks_module

    fake_repo = AsyncMock()
    fake_repo.list_active_agents_with_skill.return_value = [agent_a, agent_b]
    monkeypatch.setattr(webhooks_module, "AgentRepository", lambda db: fake_repo)

    exec_ids = [uuid.uuid4(), uuid.uuid4()]
    fake_exec_service = AsyncMock()
    fake_exec_service.create_execution.side_effect = [
        Execution(id=exec_ids[0], agent_id=agent_a.id, org_id=agent_a.org_id, goal="g", status="PENDING"),
        Execution(id=exec_ids[1], agent_id=agent_b.id, org_id=agent_b.org_id, goal="g", status="PENDING"),
    ]
    monkeypatch.setattr(webhooks_module, "ExecutionService", lambda exec_repo: fake_exec_service)

    background_tasks = BackgroundTasks()
    response = await jira_issue_created(
        payload=JiraIssueWebhook(issue_key="SCRUM-7", summary="Login broken", description="Can't log in"),
        background_tasks=background_tasks,
        x_webhook_secret="test-secret",
        db=AsyncMock(),
        llm_service=AsyncMock(),
    )

    assert response["issue_key"] == "SCRUM-7"
    assert set(response["executions_started"]) == {str(exec_ids[0]), str(exec_ids[1])}

    assert len(background_tasks.tasks) == 2
    assert all(t.func is run_execution for t in background_tasks.tasks)
    queued_ids = {t.kwargs["execution_id"] for t in background_tasks.tasks}
    assert queued_ids == set(exec_ids)

    goal = fake_exec_service.create_execution.call_args_list[0].kwargs["goal"]
    assert "SCRUM-7" in goal
    assert "Login broken" in goal
    assert "Can't log in" in goal


@pytest.mark.asyncio
async def test_no_eligible_agents_starts_nothing(monkeypatch):
    from app.api.v1 import webhooks as webhooks_module

    fake_repo = AsyncMock()
    fake_repo.list_active_agents_with_skill.return_value = []
    monkeypatch.setattr(webhooks_module, "AgentRepository", lambda db: fake_repo)

    background_tasks = BackgroundTasks()
    response = await jira_issue_created(
        payload=JiraIssueWebhook(issue_key="SCRUM-8", summary="s", description=""),
        background_tasks=background_tasks,
        x_webhook_secret="test-secret",
        db=AsyncMock(),
        llm_service=AsyncMock(),
    )

    assert response["executions_started"] == []
    assert len(background_tasks.tasks) == 0
