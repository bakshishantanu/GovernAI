from unittest.mock import AsyncMock, MagicMock

from app.runtime.llm.gemini import GeminiProvider


def _mock_client(response_json: dict) -> AsyncMock:
    response = MagicMock()
    response.json.return_value = response_json
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post.return_value = response
    return client


async def test_chat_parses_response_and_usage():
    client = _mock_client(
        {
            "candidates": [{"content": {"parts": [{"text": "hello"}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5, "totalTokenCount": 15},
        }
    )
    provider = GeminiProvider(api_key="test-key", client=client)

    result = await provider.chat([{"role": "user", "content": "hi"}])

    assert result.content == "hello"
    assert result.provider == "gemini"
    assert result.usage.total_tokens == 15
    assert result.finish_reason == "STOP"


async def test_chat_sends_api_key_header():
    client = _mock_client({"candidates": [{"content": {"parts": [{"text": ""}]}}], "usageMetadata": {}})
    provider = GeminiProvider(api_key="secret", client=client)

    await provider.chat([{"role": "user", "content": "hi"}])

    _, kwargs = client.post.call_args
    assert kwargs["headers"]["x-goog-api-key"] == "secret"


async def test_system_message_becomes_system_instruction():
    client = _mock_client({"candidates": [{"content": {"parts": [{"text": ""}]}}], "usageMetadata": {}})
    provider = GeminiProvider(api_key="k", client=client)

    await provider.chat(
        [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "hi"},
        ]
    )

    _, kwargs = client.post.call_args
    payload = kwargs["json"]
    assert payload["systemInstruction"]["parts"][0]["text"] == "You are helpful."
    assert len(payload["contents"]) == 1


async def test_chat_parses_function_call():
    client = _mock_client(
        {
            "candidates": [
                {
                    "content": {
                        "parts": [{"functionCall": {"name": "search_documents", "args": {"query": "policy"}}}]
                    },
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {},
        }
    )
    provider = GeminiProvider(api_key="k", client=client)

    result = await provider.chat([{"role": "user", "content": "search"}])

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_documents"
    assert result.tool_calls[0].arguments == {"query": "policy"}
