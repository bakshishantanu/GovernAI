from __future__ import annotations

import hmac

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_llm_service
from app.api.execution_runner import run_execution
from app.config import settings
from app.domain.agents.repository import AgentRepository
from app.domain.executions.repository import ExecutionRepository
from app.domain.executions.service import ExecutionService
from app.runtime.llm.service import LLMService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class JiraIssueWebhook(BaseModel):
    """Body this endpoint expects. Jira Automation's "Send web request"
    action lets a rule author define its own JSON body with smart values --
    this is the shape the rule must be configured to send, e.g.:

        {
          "issue_key": "{{issue.key}}",
          "summary": "{{issue.summary}}",
          "description": "{{issue.description}}"
        }
    """

    issue_key: str
    summary: str
    description: str = ""


def _verify_webhook_secret(provided: str | None) -> None:
    if not settings.JIRA_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="JIRA_WEBHOOK_SECRET is not configured on this server.",
        )
    # Constant-time comparison -- this is a bearer secret, not a public id.
    if not provided or not hmac.compare_digest(provided, settings.JIRA_WEBHOOK_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret")


@router.post("/jira", status_code=status.HTTP_202_ACCEPTED)
async def jira_issue_created(
    payload: JiraIssueWebhook,
    background_tasks: BackgroundTasks,
    x_webhook_secret: str | None = Header(default=None),
    # Query-param alternative to the X-Webhook-Secret header, for callers that
    # cannot reliably attach custom headers (Jira Automation drops them).
    secret: str | None = None,
    db: AsyncSession = Depends(get_db),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Starts a run, unattended, on every ACTIVE agent that has the
    Ticketing skill -- for whoever built that agent, when a new Jira issue
    is raised. No human clicks "run"; this is the second entry point into
    the agent runtime alongside POST /executions/.

    Deliberately un-scoped to a single org/project for now: any agent_builder
    who has wired up an agent with the Ticketing skill gets it triggered.
    Routing by which Jira project maps to which org/agent is a real problem
    once there's more than one org using this, but isn't one yet.
    """
    _verify_webhook_secret(x_webhook_secret or secret)

    agent_repo = AgentRepository(db)
    exec_service = ExecutionService(exec_repo=ExecutionRepository(db))

    agents = await agent_repo.list_active_agents_with_skill("ticketing")

    goal = (
        f"A new ticket was raised: {payload.issue_key} - {payload.summary}\n\n"
        f"{payload.description}\n\n"
        "Read the ticket, decide what it needs, and draft a reply."
    )

    started = []
    for agent in agents:
        execution = await exec_service.create_execution(
            agent_id=agent.id,
            org_id=agent.org_id,
            goal=goal,
        )
        await db.commit()
        await db.refresh(execution)

        background_tasks.add_task(
            run_execution,
            execution_id=execution.id,
            agent_id=agent.id,
            org_id=agent.org_id,
            goal=goal,
            system_prompt=None,
            max_steps=10,
            llm_service=llm_service,
        )
        started.append(str(execution.id))

    return {"issue_key": payload.issue_key, "executions_started": started}
