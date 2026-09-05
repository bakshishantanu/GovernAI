from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_db,
    get_agent_service,
    get_execution_service,
    get_llm_service,
)
from app.api.sse import SSE_HEADERS, format_sse, stream as sse_stream
from app.domain.auth.middleware import get_current_user
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.execution import ExecutionCreate, ExecutionResponse
from app.domain.agents.service import AgentService
from app.domain.executions.service import ExecutionService
from app.runtime.llm.service import LLMService
from app.api.execution_runner import run_execution
from app.infrastructure.event_bus import Event

router = APIRouter(prefix="/executions", tags=["executions"])


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
    )
    # Committed before the task is queued: the run opens its own session and
    # must be able to see this row.
    await db.commit()
    # `steps` must be refreshed by name as well. `ExecutionResponse` includes
    # the collection, and a plain refresh leaves it expired — serialising it
    # then triggers a lazy load inside the async context and raises
    # MissingGreenlet, so this endpoint returned 500 before the run ever
    # started. A brand-new execution has no steps; this loads the empty list.
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
    """
    executions = await exec_service.list_executions_for_org(current_user.org_id)
    return Envelope(data=executions)


@router.get("/{execution_id}", response_model=Envelope[ExecutionResponse])
async def get_execution_detail(
    execution_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    exec_service: ExecutionService = Depends(get_execution_service),
):
    """
    Get detailed execution progress, status, and final answer.
    """
    execution = await exec_service.get_execution(execution_id)
    if not execution or execution.org_id != current_user.org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )
    return Envelope(data=execution)


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

    async def on_heartbeat() -> tuple[str | None, bool]:
        current = await exec_service.get_execution(execution_id)
        if current is None:
            return None, False  # the run vanished; nothing left to stream
        if current.status not in TERMINAL_STATUSES:
            return None, True  # still going; a keep-alive is sent instead
        done = format_sse(
            "done",
            {
                "status": current.status,
                "result": current.result,
                "error": current.error,
                "completed_at": current.completed_at,
            },
        )
        return done, False  # final frame, then close

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
