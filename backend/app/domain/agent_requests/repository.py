from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent_requests.models import AgentRequest


class AgentRequestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_request(self, request_id: UUID) -> AgentRequest | None:
        result = await self.session.execute(
            select(AgentRequest).where(AgentRequest.id == request_id)
        )
        return result.scalar_one_or_none()

    async def create_request(self, request: AgentRequest) -> AgentRequest:
        self.session.add(request)
        return request

    async def claim_request(self, request_id: UUID, builder_id: UUID) -> bool:
        """Atomically claim a PENDING request using optimistic locking."""
        from datetime import datetime, timezone

        result = await self.session.execute(
            update(AgentRequest)
            .where(AgentRequest.id == request_id, AgentRequest.status == "PENDING")
            .values(status="CLAIMED", builder_id=builder_id, claimed_at=datetime.now(timezone.utc))
        )
        return result.rowcount > 0

    async def flush(self) -> None:
        await self.session.flush()

    async def list_requests(
        self,
        org_id: UUID,
        requester_id: UUID | None = None,
        builder_id: UUID | None = None,
        status: str | None = None,
    ) -> list[AgentRequest]:
        query = select(AgentRequest).where(AgentRequest.org_id == org_id)
        if requester_id:
            query = query.where(AgentRequest.requester_id == requester_id)
        if builder_id:
            query = query.where(AgentRequest.builder_id == builder_id)
        if status:
            query = query.where(AgentRequest.status == status)

        query = query.order_by(AgentRequest.created_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())
