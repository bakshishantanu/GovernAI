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


def test_the_configured_models_have_a_pricing_entry():
    """Reads the models actually configured, rather than naming them literally.

    The earlier version of this test asserted the string "gemini-2.5-flash"
    was in the table. That is precisely what it was supposed to protect, and
    it failed to: when LLM_FALLBACK_MODEL moved to gemini-3.6-flash (because
    2.5 began answering 404), the literal was still in the table, so the test
    stayed green while every real fallback call priced at $0.00.

    A test that hardcodes the value it is checking cannot notice the value
    changing. Reading settings is the whole point.
    """
    from app.config import settings

    assert settings.LLM_PRIMARY_MODEL in PRICING_TIERS, (
        f"LLM_PRIMARY_MODEL is {settings.LLM_PRIMARY_MODEL!r} with no entry in "
        "PRICING_TIERS, so every call on it records $0.00"
    )
    assert settings.LLM_FALLBACK_MODEL in PRICING_TIERS, (
        f"LLM_FALLBACK_MODEL is {settings.LLM_FALLBACK_MODEL!r} with no entry in "
        "PRICING_TIERS, so every fallback call records $0.00"
    )


def test_the_current_fallback_model_is_priced_not_free():
    """The specific regression: gemini-3.6-flash replaced gemini-2.5-flash as
    the fallback, and was unpriced for a day."""
    assert PRICING_TIERS["gemini-3.6-flash"]["prompt"] > 0
    assert PRICING_TIERS["gemini-3.6-flash"]["completion"] > 0


@pytest.mark.asyncio
async def test_an_unpriced_model_is_warned_about_loudly(caplog):
    """Zero-cost is survivable; zero-cost *in silence* is not. BudgetGuard
    sums these same rows, so an unpriced model has no budget cap at all."""
    service = CostService(cost_repo=AsyncMock(), event_bus=AsyncMock())

    with caplog.at_level("WARNING"):
        await service.record_llm_cost(
            org_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
            execution_id=uuid.uuid4(),
            model="some-brand-new-model-nobody-priced-yet",
            prompt_tokens=1_000,
            completion_tokens=1_000,
        )

    assert "No pricing for model" in caplog.text
    assert "some-brand-new-model-nobody-priced-yet" in caplog.text


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
