from __future__ import annotations

from uuid import UUID

from app.domain.ticket_drafts.service import TicketDraftService
from app.skills.ticketing import TicketDraftStore


class ExecutionScopedDraftStore(TicketDraftStore):
    """Binds the drafting tool to the run that is using it.

    A tool only ever receives the arguments the model produced, so the owning
    org/agent/execution have to be attached here, at construction time, by
    whoever is setting the run up (see api/execution_runner.py).
    """

    def __init__(
        self,
        service: TicketDraftService,
        *,
        org_id: UUID,
        agent_id: UUID,
        execution_id: UUID | None = None,
    ) -> None:
        self._service = service
        self._org_id = org_id
        self._agent_id = agent_id
        self._execution_id = execution_id

    async def save_draft(self, ticket_id: str, body: str) -> str:
        draft = await self._service.create_draft(
            org_id=self._org_id,
            agent_id=self._agent_id,
            execution_id=self._execution_id,
            ticket_id=ticket_id,
            body=body,
        )
        return str(draft.id)
