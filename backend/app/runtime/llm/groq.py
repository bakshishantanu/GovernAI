import json

import httpx

from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall


class GroqProvider(LLMProvider):
    """Groq's chat completions API — OpenAI-compatible request/response shape."""

    name = "groq"
    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "llama-3.3-70b-versatile",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._client = client or httpx.AsyncClient(timeout=30.0)

    async def chat(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        response = await self._client.post(
            self.BASE_URL,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        message = choice["message"]
        usage = data.get("usage", {})

        tool_calls = [
            ToolCall(
                id=tc["id"],
                name=tc["function"]["name"],
                arguments=_parse_arguments(tc["function"]["arguments"]),
            )
            for tc in (message.get("tool_calls") or [])
        ]

        return LLMResponse(
            content=message.get("content") or "",
            model=data.get("model", self._model),
            provider=self.name,
            usage=TokenUsage(
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            ),
            finish_reason=choice.get("finish_reason"),
            tool_calls=tool_calls,
        )


def _parse_arguments(raw: str | dict) -> dict:
    if isinstance(raw, dict):
        return raw
    return json.loads(raw)
