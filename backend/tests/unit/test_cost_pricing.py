"""Regression tests for PRICING_TIERS actually pricing the real providers.

Found live, 2026-09-09: the first real LLM call this project ever made (once
a real Groq key was configured) landed with `cost_usd: 0.0`, because the
pricing table only knew two OpenAI model names and this app has never had an
OpenAI provider - only Groq (`openai/gpt-oss-20b`) and Gemini
(`gemini-2.5-flash`). These tests pin the real per-million-token rates so a
future change to the table can't silently zero them out again.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.domain.costs.service import PRICING_TIERS, CostService


@pytest.mark.asyncio
async def test_groq_model_is_priced_not_free():
    repo = AsyncMock()
    bus = AsyncMock()
    service = CostService(cost_repo=repo, event_bus=bus)

    await service.record_llm_cost(
        org_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        model="openai/gpt-oss-20b",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    recorded_event = repo.record_cost.await_args.args[0]
    assert recorded_event.cost_usd == pytest.approx(0.075 + 0.30)


@pytest.mark.asyncio
async def test_gemini_model_is_priced_not_free():
    repo = AsyncMock()
    bus = AsyncMock()
    service = CostService(cost_repo=repo, event_bus=bus)

    await service.record_llm_cost(
        org_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        model="gemini-2.5-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    recorded_event = repo.record_cost.await_args.args[0]
    assert recorded_event.cost_usd == pytest.approx(0.30 + 2.50)


@pytest.mark.asyncio
async def test_current_gemini_fallback_model_is_priced_not_free():
    """gemini-3.6-flash shipped as LLM_FALLBACK_MODEL on 2026-09-12 with no
    pricing entry, silently pricing every fallback call at $0.00 - not just a
    wrong dashboard number, but a governance hole, since BudgetGuard sums
    these same rows and can never cap spend on a model priced at $0.00."""
    repo = AsyncMock()
    bus = AsyncMock()
    service = CostService(cost_repo=repo, event_bus=bus)

    await service.record_llm_cost(
        org_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        model="gemini-3.6-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )

    recorded_event = repo.record_cost.await_args.args[0]
    assert recorded_event.cost_usd == pytest.approx(0.75 + 3.75)


def test_both_real_providers_have_a_pricing_entry():
    """Reads the live settings rather than hardcoding the model names, so
    this actually fails when either model is switched without updating the
    pricing table - a hardcoded name would stay true while the real value
    moved out from under it, which is exactly how gemini-3.6-flash shipped
    unpriced on 2026-09-12."""
    assert settings.LLM_PRIMARY_MODEL in PRICING_TIERS
    assert settings.LLM_FALLBACK_MODEL in PRICING_TIERS


@pytest.mark.asyncio
async def test_an_unrecognised_model_still_falls_back_to_free_not_an_error():
    """The fallback exists on purpose - a model with no known rate shouldn't
    crash a run, it should record honestly-unpriced spend rather than fail
    the whole execution."""
    repo = AsyncMock()
    bus = AsyncMock()
    service = CostService(cost_repo=repo, event_bus=bus)

    await service.record_llm_cost(
        org_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        execution_id=uuid.uuid4(),
        model="some-brand-new-model-nobody-priced-yet",
        prompt_tokens=1_000,
        completion_tokens=1_000,
    )

    recorded_event = repo.record_cost.await_args.args[0]
    assert recorded_event.cost_usd == 0
