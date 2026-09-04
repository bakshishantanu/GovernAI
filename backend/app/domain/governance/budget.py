"""Live budget enforcement — the platform's headline governance control.

FRD-11 requires that before every billable call the agent's accumulated spend is
checked against its cap, and that an agent which would exceed the cap is denied
*and automatically suspended*. Until now cost was recorded after each LLM call
and never read back, so the cap existed only on paper.

Two deliberate shortcuts, both flagged for follow-up:

1. **The cap comes from configuration, not from the agent.** There is no
   `budget_usd` column on `agents` or `agent_passports`, and adding one means a
   migration in P3's territory. A single org-wide default is enough to enforce
   and demonstrate the rule; a per-agent override is a later column, and only
   `resolve_cap()` has to change.
2. **The window is a rolling 24 hours**, matching the FRD's "rolling 24h" wording,
   measured from now rather than from a stored window start.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable, Protocol
from uuid import UUID

#: Org-wide default cap in USD when nothing more specific is configured.
DEFAULT_BUDGET_USD_24H = 5.0

#: How far back spend is totalled.
BUDGET_WINDOW = timedelta(hours=24)


def resolve_cap(agent_id: UUID) -> float:
    """The spend ceiling for one agent over the window.

    Currently one org-wide number from the environment. When a per-agent cap
    column exists this is the only function that needs to change.
    """
    raw = os.environ.get("AGENT_BUDGET_USD_24H", "").strip()
    if not raw:
        return DEFAULT_BUDGET_USD_24H
    try:
        cap = float(raw)
    except ValueError:
        return DEFAULT_BUDGET_USD_24H
    # A negative or zero cap would silently disable every agent, which is far
    # more likely a typo than an intention.
    return cap if cap > 0 else DEFAULT_BUDGET_USD_24H


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    spend_usd: float
    cap_usd: float
    reason: str = ""

    @property
    def remaining_usd(self) -> float:
        return max(self.cap_usd - self.spend_usd, 0.0)


class SpendReader(Protocol):
    """The slice of the cost repository this guard needs."""

    async def get_total_cost_for_agent(self, agent_id: UUID, since: datetime) -> float: ...


class BudgetGuard:
    """Answers one question: may this agent still spend money?

    `on_breach` is called once, when an agent first crosses its cap, so the
    caller can suspend it. It is injected rather than imported so this stays
    testable and does not depend on the kill-switch service.
    """

    def __init__(
        self,
        spend_reader: SpendReader,
        on_breach: Callable[[UUID, UUID, str], Awaitable[None]] | None = None,
        cap_resolver: Callable[[UUID], float] = resolve_cap,
    ) -> None:
        self._spend = spend_reader
        self._on_breach = on_breach
        self._cap_for = cap_resolver

    async def check(self, agent_id: UUID, org_id: UUID) -> BudgetDecision:
        cap = self._cap_for(agent_id)
        since = datetime.now(timezone.utc) - BUDGET_WINDOW

        try:
            spend = await self._spend.get_total_cost_for_agent(agent_id, since)
        except Exception as exc:
            # Fail closed, exactly like the policy engine: if we cannot prove
            # the agent is under budget, it does not get to spend.
            return BudgetDecision(
                allowed=False,
                spend_usd=0.0,
                cap_usd=cap,
                reason=f"Budget could not be verified: {exc}",
            )

        if spend < cap:
            return BudgetDecision(allowed=True, spend_usd=spend, cap_usd=cap)

        reason = (
            f"Budget exceeded: ${spend:.2f} of ${cap:.2f} spent in the last 24h. "
            "The agent has been suspended."
        )

        if self._on_breach is not None:
            try:
                await self._on_breach(agent_id, org_id, reason)
            except Exception:
                # Never let a failed suspension turn into an allowed call.
                # The denial below still stands.
                pass

        return BudgetDecision(
            allowed=False, spend_usd=spend, cap_usd=cap, reason=reason
        )
