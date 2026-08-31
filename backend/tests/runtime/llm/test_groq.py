from unittest.mock import AsyncMock, MagicMock

from app.runtime.llm.groq import GroqProvider


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
            "model": "llama-3.3-70b-versatile",
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )
    provider = GroqProvider(api_key="test-key", client=client)

    result = await provider.chat([{"role": "user", "content": "hi"}])

    assert result.content == "hello"
    assert result.provider == "groq"
    assert result.usage.total_tokens == 15
    assert result.finish_reason == "stop"
    assert result.tool_calls == []


async def test_chat_sends_bearer_auth_header():
    client = _mock_client(
        {
            "model": "m",
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
            "usage": {},
        }
    )
    provider = GroqProvider(api_key="secret-key", client=client)

    await provider.chat([{"role": "user", "content": "hi"}])

    _, kwargs = client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"


async def test_chat_parses_tool_calls():
    client = _mock_client(
        {
            "model": "m",
            "choices": [
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {"name": "read_ticket", "arguments": '{"ticket_id": 42}'},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    )
    provider = GroqProvider(api_key="k", client=client)

    result = await provider.chat([{"role": "user", "content": "read ticket 42"}])

    assert result.content == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "read_ticket"
    assert result.tool_calls[0].arguments == {"ticket_id": 42}
