from __future__ import annotations
import asyncio

from app.runtime.llm.base import LLMProvider, LLMResponse
from app.runtime.llm.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError


class AllProvidersFailedError(Exception):
    """Raised when every configured provider failed (or was circuit-broken)."""

    def __init__(self, attempts: list[str]):
        self.attempts = attempts
        super().__init__(f"All LLM providers failed: {'; '.join(attempts)}")


class LLMService:
    """Resilient LLM calling on top of one or more LLMProvider implementations.

    Providers are tried in the given order (primary first, fallback second, ...).
    Each provider gets `max_retries_per_provider` attempts with exponential
    backoff before moving on to the next provider. A CircuitBreaker skips a
    provider outright while it's tripped open, per FRD-06.
    """

    def __init__(
        self,
        providers: list[LLMProvider],
        circuit_breaker: CircuitBreaker | None = None,
        max_retries_per_provider: int = 2,
        base_backoff_seconds: float = 1.0,
        sleep=asyncio.sleep,
    ) -> None:
        if not providers:
            raise ValueError("LLMService needs at least one provider")
        self._providers = providers
        self._breaker = circuit_breaker or CircuitBreaker()
        self._max_retries = max_retries_per_provider
        self._base_backoff = base_backoff_seconds
        self._sleep = sleep

    async def chat(self, messages: list[dict], **kwargs) -> LLMResponse:
        attempts: list[str] = []

        for provider in self._providers:
            try:
                self._breaker.before_call(provider.name)
            except CircuitBreakerOpenError as exc:
                attempts.append(f"{provider.name}: {exc}")
                continue

            response = await self._try_provider(provider, messages, attempts, **kwargs)
            if response is not None:
                return response

        raise AllProvidersFailedError(attempts)

    async def _try_provider(
        self, provider: LLMProvider, messages: list[dict], attempts: list[str], **kwargs
    ) -> LLMResponse | None:
        for attempt in range(self._max_retries):
            try:
                response = await provider.chat(messages, **kwargs)
            except Exception as exc:
                attempts.append(f"{provider.name} attempt {attempt + 1}/{self._max_retries}: {exc}")
                self._breaker.record_failure(provider.name)
                if attempt < self._max_retries - 1:
                    await self._sleep(self._base_backoff * (2**attempt))
                continue
            else:
                self._breaker.record_success(provider.name)
                return response
        return None
