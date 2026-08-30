import httpx

from app.runtime.llm.base import LLMProvider, LLMResponse, TokenUsage, ToolCall

_ROLE_MAP = {"assistant": "model", "user": "user"}


class GeminiProvider(LLMProvider):
    """Google Gemini's generateContent API — request/response shape differs from
    OpenAI's, so this provider translates to/from the shared LLMProvider interface.
    """

    name = "gemini"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
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
        system_instruction, contents = _to_gemini_contents(messages)

        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_instruction is not None:
            payload["systemInstruction"] = system_instruction
        if tools:
            payload["tools"] = [{"functionDeclarations": [_to_gemini_function(t) for t in tools]}]
        if max_tokens is not None:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens

        url = f"{self.BASE_URL}/{self._model}:generateContent"
        response = await self._client.post(
            url,
            headers={"x-goog-api-key": self._api_key},
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])
        text = "".join(p["text"] for p in parts if "text" in p)
        tool_calls = [
            ToolCall(id=f"call_{i}", name=p["functionCall"]["name"], arguments=p["functionCall"].get("args", {}))
            for i, p in enumerate(parts)
            if "functionCall" in p
        ]

        usage = data.get("usageMetadata", {})

        return LLMResponse(
            content=text,
            model=self._model,
            provider=self.name,
            usage=TokenUsage(
                prompt_tokens=usage.get("promptTokenCount", 0),
                completion_tokens=usage.get("candidatesTokenCount", 0),
                total_tokens=usage.get("totalTokenCount", 0),
            ),
            finish_reason=candidate.get("finishReason"),
            tool_calls=tool_calls,
        )


def _to_gemini_contents(messages: list[dict]) -> tuple[dict | None, list[dict]]:
    system_parts = [m["content"] for m in messages if m["role"] == "system"]
    system_instruction = {"parts": [{"text": "\n".join(system_parts)}]} if system_parts else None

    contents = [
        {"role": _ROLE_MAP.get(m["role"], "user"), "parts": [{"text": m["content"]}]}
        for m in messages
        if m["role"] != "system"
    ]
    return system_instruction, contents


def _to_gemini_function(openai_tool: dict) -> dict:
    fn = openai_tool["function"]
    return {
        "name": fn["name"],
        "description": fn["description"],
        "parameters": fn["parameters"],
    }
