from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from app.domain.agent_requests.models import AgentRequest
from app.domain.agent_requests.repository import AgentRequestRepository
from app.infrastructure.event_bus import Event, EventBus


class RequestNotFoundError(Exception):
    pass


class RequestAlreadyClaimedError(Exception):
    pass


class InvalidStateTransitionError(Exception):
    pass


class AgentRequestService:
    def __init__(self, request_repo: AgentRequestRepository, event_bus: EventBus | None = None):
        self.request_repo = request_repo
        self.event_bus = event_bus

    async def _emit_status(self, req: AgentRequest) -> None:
        if self.event_bus:
            import inspect

            res = self.event_bus.publish(
                Event(
                    id=uuid4(),
                    timestamp=datetime.now(timezone.utc),
                    type="request_status",
                    payload={
                        "request_id": str(req.id),
                        "org_id": str(req.org_id),
                        "status": req.status,
                        "title": req.title,
                    },
                )
            )
            if inspect.isawaitable(res):
                await res

    async def create_request(
        self,
        org_id: UUID,
        requester_id: UUID,
        title: str,
        description: str,
        requested_skills: list[str],
    ) -> AgentRequest:
        req = AgentRequest(
            id=uuid4(),
            org_id=org_id,
            requester_id=requester_id,
            title=title,
            description=description,
            requested_skills=requested_skills,
            status="PENDING",
        )
        await self.request_repo.create_request(req)
        await self.request_repo.flush()
        await self._emit_status(req)
        return req

    async def claim_request(self, request_id: UUID, builder_id: UUID) -> AgentRequest:
        req = await self.request_repo.get_request(request_id)
        if not req:
            raise RequestNotFoundError("Request not found")

        success = await self.request_repo.claim_request(request_id, builder_id)
        if not success:
            # If it failed to update, it's either already claimed or not PENDING
            current_req = await self.request_repo.get_request(request_id)
            if current_req and current_req.status != "PENDING":
                raise RequestAlreadyClaimedError("Request is no longer pending")
            raise InvalidStateTransitionError("Could not claim request")

        updated = await self.request_repo.get_request(request_id)
        await self._emit_status(updated)
        return updated

    async def fulfill_request(self, request_id: UUID, agent_id: UUID) -> AgentRequest:
        req = await self.request_repo.get_request(request_id)
        if not req:
            raise RequestNotFoundError("Request not found")

        if req.status != "CLAIMED":
            raise InvalidStateTransitionError("Only CLAIMED requests can be fulfilled")

        req.status = "FULFILLED"
        req.agent_id = agent_id
        req.fulfilled_at = datetime.now(timezone.utc)
        await self.request_repo.flush()
        await self._emit_status(req)
        return req

    async def cancel_request(self, request_id: UUID) -> AgentRequest:
        req = await self.request_repo.get_request(request_id)
        if not req:
            raise RequestNotFoundError("Request not found")

        if req.status not in ("PENDING", "CLAIMED"):
            raise InvalidStateTransitionError("Only PENDING or CLAIMED requests can be cancelled")

        req.status = "CANCELLED"
        await self.request_repo.flush()
        await self._emit_status(req)
        return req
