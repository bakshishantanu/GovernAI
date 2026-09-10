import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.domain.costs.models import CostEvent
from app.domain.costs.repository import CostRepository
from app.infrastructure.event_bus import Event, EventBus

# A mock pricing dictionary. In production, this would be fetched from a config or database.
#
# `gpt-4o`/`gpt-3.5-turbo` are OpenAI models this app has never had a provider
# for - real Groq/Gemini spend was silently pricing at $0.00 until these two
# real entries were added (found live, 2026-09-09, the first time a real key
# ever produced a real cost event). Rates are each provider's own published
# per-million-token price, checked directly against their own docs the same
# day rather than an aggregator: Groq's `console.groq.com/docs/models` for
# `openai/gpt-oss-20b` (LLM_PRIMARY_MODEL), Google's own
# `ai.google.dev/gemini-api/docs/pricing` for `gemini-2.5-flash`
# (LLM_FALLBACK_MODEL, standard/paid tier, text input). These will drift as
# providers reprice - worth re-checking periodically, not a one-time fix.
PRICING_TIERS = {
    "gpt-4o": {"prompt": 5.00 / 1_000_000, "completion": 15.00 / 1_000_000},
    "gpt-3.5-turbo": {"prompt": 0.50 / 1_000_000, "completion": 1.50 / 1_000_000},
    "openai/gpt-oss-20b": {"prompt": 0.075 / 1_000_000, "completion": 0.30 / 1_000_000},
    "gemini-2.5-flash": {"prompt": 0.30 / 1_000_000, "completion": 2.50 / 1_000_000},
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
        completion_tokens: int,
    ):
        pricing = PRICING_TIERS.get(model, {"prompt": 0, "completion": 0})
        cost_usd = (prompt_tokens * pricing["prompt"]) + (completion_tokens * pricing["completion"])

        total_tokens = prompt_tokens + completion_tokens

        event = CostEvent(
            id=uuid.uuid4(),
            org_id=org_id,
            agent_id=agent_id,
            execution_id=execution_id,
            event_type="LLM_CALL",
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            timestamp=datetime.now(timezone.utc),
        )
        await self.cost_repo.record_cost(event)
        await self.event_bus.publish(
            Event.create(
                "cost.llm.incurred",
                {
                    "execution_id": str(execution_id),
                    "agent_id": str(agent_id),
                    "org_id": str(org_id),
                    "cost_usd": cost_usd,
                    "tokens": total_tokens,
                },
            )
        )
