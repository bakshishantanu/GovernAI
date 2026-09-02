import uuid
from uuid import UUID
from datetime import datetime, timezone
from app.domain.costs.models import CostEvent
from app.domain.costs.repository import CostRepository
from app.infrastructure.event_bus import Event, EventBus

# A mock pricing dictionary. In production, this would be fetched from a config or database.
PRICING_TIERS = {
    "gpt-4o": {"prompt": 5.00 / 1_000_000, "completion": 15.00 / 1_000_000},
    "gpt-3.5-turbo": {"prompt": 0.50 / 1_000_000, "completion": 1.50 / 1_000_000},
}

class CostService:
    def __init__(self, cost_repo: CostRepository, event_bus: EventBus):
        self.cost_repo = cost_repo
        self.event_bus = event_bus

    async def record_llm_cost(
        self,
        org_id: UUID,
        agent_id: UUID,
        execution_id: UUID,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ):
        pricing = PRICING_TIERS.get(model, {"prompt": 0, "completion": 0})
        cost_usd = (prompt_tokens * pricing["prompt"]) + (completion_tokens * pricing["completion"])
        
        total_tokens = prompt_tokens + completion_tokens
        
        event = CostEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            agent_id=agent_id,
            execution_id=execution_id,
            event_type="llm_inference",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now(timezone.utc)
        )
        await self.cost_repo.record_cost(event)
        await self.event_bus.publish(Event.create("cost.llm.incurred", {
            "execution_id": str(execution_id),
            "cost_usd": cost_usd,
            "tokens": total_tokens
        }))
