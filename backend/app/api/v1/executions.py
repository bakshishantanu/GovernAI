from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

import app.domain.agents.models  # noqa: F401  (used via a fully-qualified reference)
from app.api.deps import (
    get_agent_service,
    get_cost_repository,
    get_db,
    get_execution_service,
    get_llm_service,
)
from app.api.execution_runner import run_execution
from app.api.schemas.audit import AuditEventResponse
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.execution import (
    ExecutionCreate,
    ExecutionResponse,
    ExecutionTimelineResponse,
)
from app.api.sse import SSE_HEADERS, format_sse
from app.api.sse import stream as sse_stream

# Reused rather than reimplemented: a CostEvent row cannot simply be
# model_validate'd (the column is `metadata` in the database but
# `metadata_json` on the model, and the event type needs translating), and a
# second copy of that mapping here would be free to drift from the one the
# costs routes use.
from app.api.v1.costs import _to_response as cost_event_to_response
from app.domain.agents.models import Agent
from app.domain.agents.service import AgentService
from app.domain.audit.repository import AuditRepository
from app.domain.auth.middleware import get_current_user
from app.domain.costs.repository import CostRepository
from app.domain.executions.service import ExecutionService
from app.infrastructure.event_bus import Event
from app.runtime.llm.service import LLMService

router = APIRouter(prefix="/executions", tags=["executions"])

#: Mirrors `api/v1/costs.py`'s own `_EVENT_TYPE_ALIASES` -- kept local rather
#: than imported across routers for a two-line dict; both read the same
#: `CostEvent.event_type` values and must stay in agreement if either changes.
@router.post(
    "/",
    response_model=Envelope[ExecutionResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_and_run_execution(
    payload: ExecutionCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    agent_service: AgentService = Depends(get_agent_service),
    exec_service: ExecutionService = Depends(get_execution_service),
    llm_service: LLMService = Depends(get_llm_service),
):
    """Start an agent run and return straight away.

    Returns **202 Accepted** with the execution id. The run itself happens after
    the response is sent, so the caller can immediately open
    `GET /executions/{id}/stream` and watch each tool call, allow and denial as
    it happens.

    This used to `await` the whole run before responding, which meant the run
    was already over by the time the caller had an id — the live view had
    nothing left to show.
    """
    agent = await agent_service.agent_repo.get_agent(payload.agent_id)
    if not agent or agent.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found in your organization",
        )

    # Owner or assignee, not a role branch: running an agent is a "use"
    # action, open to whoever built it or whoever it was handed to.
    if current_user.role != "admin" and current_user.id not in (
        agent.owner_id,
        agent.assigned_user_id,
    ):
        raise HTTPException(status_code=403, detail="Not authorized to execute this agent")

    if not agent.passport or agent.passport.lifecycle_state != "ACTIVE":
        state = agent.passport.lifecycle_state if agent.passport else "UNKNOWN"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Agent cannot be executed: lifecycle state is '{state}'. "
                "Agent must be in 'ACTIVE' state."
            ),
        )

    execution = await exec_service.create_execution(
        agent_id=agent.id,
        org_id=current_user.org_id,
        goal=payload.goal,
        triggered_by_id=current_user.id,
    )
    # Committed before the task is queued: the run opens its own session and
    # must be able to see this row.
    await db.commit()
    await db.refresh(execution)
    # `refresh()` without `attribute_names` only reloads columns, not
    # relationships, so `steps` stays unloaded. ExecutionResponse includes
    # `steps`, and accessing an unloaded relationship during response
    # serialization lazy-loads it outside the request's async context,
    # raising MissingGreenlet — assigning `execution.steps = []` directly
    # does not avoid this, because SQLAlchemy's relationship setter reads the
    # *old* collection first to compute the diff, which triggers the exact
    # same lazy load. Refreshing `steps` explicitly is a real, awaited query
    # inside the current async context, so it loads safely.
    await db.refresh(execution, attribute_names=["steps"])

    background_tasks.add_task(
        run_execution,
        execution_id=execution.id,
        agent_id=agent.id,
        org_id=current_user.org_id,
        goal=payload.goal,
        system_prompt=payload.system_prompt,
        max_steps=payload.max_steps,
        llm_service=llm_service,
    )

    return Envelope(data=execution)


@router.get("/", response_model=Envelope[list[ExecutionResponse]])
async def list_executions(
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    List all execution runs for the current user's organization (newest first).
    Role-scoped filtering applies based on the user's role.
    """
    builder_id = current_user.id if current_user.is_builder else None
    assigned_user_id = current_user.id if current_user.is_builder else None

    executions = await exec_service.list_executions_for_org(
        current_user.org_id, builder_id=builder_id, assigned_user_id=assigned_user_id
    )
    return Envelope(data=executions)


@router.get("/{execution_id}", response_model=Envelope[ExecutionResponse])
async def get_execution_detail(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
    cost_repo: CostRepository = Depends(get_cost_repository),
):
    """
    Get detailed execution progress, status, final answer, and run-level totals.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    # Re-fetch agent to verify ownership
    agent = await exec_service.exec_repo.session.get(Agent, execution.agent_id)
    if agent:
        if current_user.role != "admin" and current_user.id not in (
            agent.owner_id,
            agent.assigned_user_id,
        ):
            raise HTTPException(status_code=403, detail="Not authorized to view this execution")

    total_cost_usd, total_tokens = await cost_repo.get_totals_for_execution(execution_id)
    response = ExecutionResponse.model_validate(execution).model_copy(
        update={"total_cost_usd": total_cost_usd, "total_tokens": total_tokens}
    )
    return Envelope(data=response)


@router.get("/{execution_id}/timeline", response_model=Envelope[ExecutionTimelineResponse])
async def get_execution_timeline(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
    cost_repo: CostRepository = Depends(get_cost_repository),
    db: AsyncSession = Depends(get_db),
):
    """The full recorded history of one run: every governed tool call and every
    LLM call, for reconstructing what happened on a run opened after the fact.

    `/stream` only ever shows events from the moment a client connects —
    nothing before that, and nothing at all for a run that had already finished
    by the time someone opened its page. This fills that gap.

    Authorization is identical to `get_execution_detail` above, deliberately
    *not* the stricter admin-only gate on `GET /costs/`: someone must be able to
    see their own run's cost history even though they cannot see the org-wide
    spend dashboard.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    agent = await exec_service.exec_repo.session.get(Agent, execution.agent_id)
    if agent:
        if (
            current_user.is_builder
            and agent.owner_id != current_user.id
            and agent.assigned_user_id != current_user.id
        ):
            raise HTTPException(status_code=403, detail="Not authorized to view this execution")

    # Only reached once the execution above is authorized — which is what makes
    # the repository's execution_id filter safe to use without also applying its
    # ownership filter.
    audit_repo = AuditRepository(db)
    audit_events = await audit_repo.get_events_for_org(
        org_id=current_user.org_id, execution_id=execution_id, limit=1000
    )
    cost_events = await cost_repo.list_costs(
        org_id=current_user.org_id, execution_id=execution_id, limit=1000
    )

    # Both repositories return newest-first; a timeline reads oldest-first.
    return Envelope(
        data=ExecutionTimelineResponse(
            execution_id=execution_id,
            governance_events=[
                AuditEventResponse.model_validate(e) for e in reversed(audit_events)
            ],
            cost_events=[cost_event_to_response(e) for e in reversed(cost_events)],
        )
    )


@router.post("/{execution_id}/cancel", response_model=Envelope[ExecutionResponse])
async def cancel_execution(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    Emergency Kill Switch: Immediately cancel/terminate an active execution.
    """
    try:
        updated = await exec_service.cancel(execution_id=execution_id, org_id=current_user.org_id)
        await db.commit()
        return Envelope(data=updated)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


#: An execution in any of these states will never produce another event.
TERMINAL_STATUSES = ("COMPLETED", "FAILED", "CANCELLED", "TERMINATED")

#: Events carrying an `execution_id`, which is what this stream filters on.
EXECUTION_SCOPED_EVENTS = (
    "audit.tool.allowed",
    "audit.tool.denied",
    "cost.llm.incurred",
)


@router.get("/{execution_id}/stream")
async def stream_execution_events(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """Live SSE stream of one execution: every tool call, decision and cost.

    Driven by the event bus, so a frame is emitted the moment a service
    publishes — not on a timer. Authorisation happens once, here, before any
    subscription exists; afterwards the stream only forwards events whose
    `execution_id` matches this already-authorised run.

    Run status is *not* published by any service, so it is re-read on the
    heartbeat rather than polled continuously. That is what closes the stream
    when the run ends.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    wanted_execution_id = str(execution_id)

    def matches(event: Event) -> bool:
        if event.type not in EXECUTION_SCOPED_EVENTS:
            return False
        # Positive match only. An event without the id is never assumed to
        # belong to this run.
        return event.payload.get("execution_id") == wanted_execution_id

    def render(event: Event) -> str:
        return format_sse(
            event.type,
            {"id": str(event.id), "at": event.timestamp, **event.payload},
        )

    def _done_frame(current) -> str:
        return format_sse(
            "done",
            {
                "status": current.status,
                "result": current.result,
                "error": current.error,
                "completed_at": current.completed_at,
            },
        )

    async def on_heartbeat() -> tuple[str | None, bool]:
        current = await exec_service.get_execution(execution_id)
        if current is None:
            return None, False  # the run vanished; nothing left to stream
        if current.status not in TERMINAL_STATUSES:
            return None, True  # still going; a keep-alive is sent instead
        return _done_frame(current), False  # final frame, then close

    initial = [
        format_sse(
            "status",
            {
                "execution_id": wanted_execution_id,
                "status": execution.status,
                "goal": execution.goal,
            },
        )
    ]

    # A run that finishes fast (the mock provider often does, in well under a
    # second) can already be terminal by the time a client opens this stream
    # — no further bus event will ever arrive for it. Without this, the
    # client would sit subscribed to the bus for nothing, waiting out a full
    # HEARTBEAT_SECONDS timeout before `on_heartbeat` ever ran, showing "no
    # result" for that whole window even though the result has been sitting
    # in the database since before the connection even opened. Short-circuit
    # entirely rather than subscribing at all: there is nothing left to wait
    # for.
    if execution.status in TERMINAL_STATUSES:
        initial.append(_done_frame(execution))

        async def _finished_stream():
            for frame in initial:
                yield frame

        return StreamingResponse(
            _finished_stream(), media_type="text/event-stream", headers=SSE_HEADERS
        )

    return StreamingResponse(
        sse_stream(
            initial=initial,
            matches=matches,
            render=render,
            on_heartbeat=on_heartbeat,
        ),
        media_type="text/event-stream",
        headers=SSE_HEADERS,
    )
