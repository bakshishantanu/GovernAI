import pytest

from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage
from app.runtime.llm.circuit_breaker import CircuitBreaker
from app.runtime.llm.service import AllProvidersFailedError, LLMService


class _ScriptedProvider(LLMProvider):
    """Fails for the first `fail_times` calls, then succeeds (or always fails)."""

    def __init__(self, name: str, fail_times: int = 0, always_fail: bool = False):
        self.name = name
        self._fail_times = fail_times
        self._always_fail = always_fail
        self.call_count = 0

    async def chat(self, messages, *, tools=None, temperature=0.7, max_tokens=None) -> LLMResponse:
        self.call_count += 1
        if self._always_fail or self.call_count <= self._fail_times:
            raise RuntimeError(f"{self.name} simulated failure #{self.call_count}")
        return LLMResponse(
            content=f"ok from {self.name}",
            model="fake-model",
            provider=self.name,
            usage=TokenUsage(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        )


async def test_succeeds_on_first_try_no_retry_needed():
    provider = _ScriptedProvider("groq")
    service = LLMService([provider], max_retries_per_provider=2)

    result = await service.chat([{"role": "user", "content": "hi"}])

    assert result.content == "ok from groq"
    assert provider.call_count == 1


async def test_retries_same_provider_before_succeeding():
    provider = _ScriptedProvider("groq", fail_times=1)
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    service = LLMService([provider], max_retries_per_provider=2, sleep=fake_sleep)

    result = await service.chat([{"role": "user", "content": "hi"}])

    assert result.provider == "groq"
    assert provider.call_count == 2
    assert sleeps == [1.0]  # base_backoff_seconds * 2**0


async def test_falls_back_to_secondary_provider_after_exhausting_primary():
    primary = _ScriptedProvider("groq", always_fail=True)
    secondary = _ScriptedProvider("gemini")

    async def fake_sleep(seconds):
        pass

    service = LLMService([primary, secondary], max_retries_per_provider=2, sleep=fake_sleep)

    result = await service.chat([{"role": "user", "content": "hi"}])

    assert result.provider == "gemini"
    assert primary.call_count == 2  # exhausted its retries
    assert secondary.call_count == 1  # succeeded first try


async def test_raises_when_all_providers_exhausted():
    primary = _ScriptedProvider("groq", always_fail=True)
    secondary = _ScriptedProvider("gemini", always_fail=True)

    async def fake_sleep(seconds):
        pass

    service = LLMService([primary, secondary], max_retries_per_provider=2, sleep=fake_sleep)

    with pytest.raises(AllProvidersFailedError) as exc_info:
        await service.chat([{"role": "user", "content": "hi"}])

    assert primary.call_count == 2
    assert secondary.call_count == 2
    assert len(exc_info.value.attempts) == 4


async def test_uses_exponential_backoff():
    provider = _ScriptedProvider("groq", fail_times=2)
    sleeps: list[float] = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)

    service = LLMService([provider], max_retries_per_provider=3, base_backoff_seconds=1.0, sleep=fake_sleep)

    await service.chat([{"role": "user", "content": "hi"}])

    assert sleeps == [1.0, 2.0]  # 1 * 2**0, then 1 * 2**1


async def test_open_circuit_skips_provider_entirely():
    breaker = CircuitBreaker(failure_threshold=1)
    breaker.record_failure("groq")  # circuit now open for groq

    primary = _ScriptedProvider("groq")  # would succeed if called - but shouldn't be
    secondary = _ScriptedProvider("gemini")

    service = LLMService([primary, secondary], circuit_breaker=breaker, max_retries_per_provider=2)

    result = await service.chat([{"role": "user", "content": "hi"}])

    assert result.provider == "gemini"
    assert primary.call_count == 0  # never called - circuit was open


def test_service_requires_at_least_one_provider():
    with pytest.raises(ValueError):
        LLMService([])
