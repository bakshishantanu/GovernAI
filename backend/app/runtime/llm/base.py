from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class TokenUsage:
    """Token counts for a single LLM call. Consumed by the cost service (FRD-11)."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


@dataclass(frozen=True)
class ToolCall:
    """A tool invocation requested by the LLM."""

    id: str
    name: str
    arguments: dict


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response shape, identical regardless of which provider answered."""

    content: str
    model: str
    provider: str
    usage: TokenUsage
    finish_reason: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """Common interface every LLM provider (Groq, Gemini, ...) implements.

    Messages follow the OpenAI chat format: [{"role": "user"|"assistant"|"system", "content": str}, ...]
    Tools follow the OpenAI function-calling format (see BaseTool.to_openai_tool()).
    """

    name: str

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        ...
