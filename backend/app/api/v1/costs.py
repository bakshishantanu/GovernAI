"""Cost reporting — the read side of the platform's headline feature.

Spend has been recorded on every LLM call since the cost service was built, but
nothing exposed it, so the figure leadership is promised had no way out of the
database. These two routes are that way out.

Every number here is aggregated in SQL from real `cost_events` rows. Nothing is
estimated, sampled or filled in.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope, PaginatedResponse
from app.api.schemas.cost import CostEventResponse, CostSummaryResponse
from app.domain.auth.middleware import get_current_user
from app.domain.costs.models import CostEvent
from app.domain.costs.repository import CostRepository

router = APIRouter(prefix="/costs", tags=["costs"])

#: The cost service writes `event_type="llm_inference"`, but the shared schema
#: declares Literal["LLM_CALL", "TOOL_CALL"]. Until the stored vocabulary and
#: the API vocabulary are reconciled (a data-model change owned by P3), the
#: route translates rather than letting real rows fail validation.
_EVENT_TYPE_ALIASES = {
    "llm_inference": "LLM_CALL",
    "llm_call": "LLM_CALL",
    "tool_call": "TOOL_CALL",
}


def get_cost_repo(db: AsyncSession = Depends(get_db)) -> CostRepository:
    return CostRepository(db)


def _to_response(event: CostEvent) -> CostEventResponse:
    """Map a stored row onto the API shape.

    Done explicitly rather than with `from_attributes` because the column is
    named `metadata` in the database but `metadata_json` on the model, and the
    event type needs translating.
    """
    return CostEventResponse(
        id=event.id,
        agent_id=event.agent_id,
        execution_id=event.execution_id,
        execution_step_id=event.execution_step_id,
        event_type=_EVENT_TYPE_ALIASES.get(
            (event.event_type or "").lower(), "TOOL_CALL"
        ),
        model=event.model,
        provider=event.provider,
        prompt_tokens=event.prompt_tokens,
        completion_tokens=event.completion_tokens,
        total_tokens=event.total_tokens,
        cost_usd=event.cost_usd,
        timestamp=event.timestamp,
        metadata=event.metadata_json,
    )


@router.get("/", response_model=PaginatedResponse[CostEventResponse])
async def list_costs(
    user: CurrentUser = Depends(get_current_user),
    agent_id: UUID | None = Query(None, description="Narrow to one agent"),
    execution_id: UUID | None = Query(None, description="Narrow to one run"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    repo: CostRepository = Depends(get_cost_repo),
):
    """Individual cost events, newest first, scoped to the caller's org."""
    events = await repo.list_costs(
        org_id=user.org_id,
        agent_id=agent_id,
        execution_id=execution_id,
        limit=limit,
        offset=offset,
    )
    return PaginatedResponse(
        data=[_to_response(e) for e in events],
        meta={"count": len(events), "limit": limit, "offset": offset},
    )


@router.get("/summary", response_model=Envelope[CostSummaryResponse])
async def cost_summary(
    user: CurrentUser = Depends(get_current_user),
    repo: CostRepository = Depends(get_cost_repo),
):
    """Total spend for the organisation, broken down by agent and by model.

    The grouping is done by the database; this only pivots the already-small
    grouped result into the shape the dashboard reads.
    """
    rows = await repo.get_costs_summary(user.org_id)

    total = 0.0
    by_agent: dict[str, float] = {}
    by_model: dict[str, float] = {}

    for row in rows:
        cost = float(row.get("total_cost_usd") or 0.0)
        total += cost

        agent_id = row.get("agent_id")
        if agent_id is not None:
            key = str(agent_id)
            by_agent[key] = by_agent.get(key, 0.0) + cost

        model = row.get("model")
        if model:
            by_model[model] = by_model.get(model, 0.0) + cost

    return Envelope(
        data=CostSummaryResponse(
            total_cost_usd=round(total, 6),
            by_agent={k: round(v, 6) for k, v in by_agent.items()},
            by_model={k: round(v, 6) for k, v in by_model.items()},
        )
    )
