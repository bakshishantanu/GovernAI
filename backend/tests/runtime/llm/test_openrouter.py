from unittest.mock import AsyncMock, MagicMock

from app.domain.costs.service import PRICING_TIERS
from app.runtime.llm.openrouter import OpenRouterProvider


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
            "model": "openai/gpt-4o-mini",
            "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }
    )
    provider = OpenRouterProvider(api_key="test-key", client=client)

    result = await provider.chat([{"role": "user", "content": "hi"}])

    assert result.content == "hello"
    assert result.provider == "openrouter"
    assert result.model == "openai/gpt-4o-mini"
    assert result.usage.total_tokens == 15
    assert result.finish_reason == "stop"
    assert result.tool_calls == []


async def test_chat_sends_bearer_auth_and_configured_model():
    client = _mock_client(
        {
            "model": "m",
            "choices": [{"message": {"content": ""}, "finish_reason": "stop"}],
            "usage": {},
        }
    )
    provider = OpenRouterProvider(api_key="secret-key", model="some/model", client=client)

    await provider.chat([{"role": "user", "content": "hi"}])

    args, kwargs = client.post.call_args
    assert args[0] == OpenRouterProvider.BASE_URL
    assert kwargs["headers"]["Authorization"] == "Bearer secret-key"
    assert kwargs["json"]["model"] == "some/model"


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
                                "function": {
                                    "name": "search_solr",
                                    "arguments": '{"collection": "knowledge_base", "query": "PRD"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    )
    provider = OpenRouterProvider(api_key="k", client=client)

    result = await provider.chat([{"role": "user", "content": "find the PRD"}])

    assert result.content == ""
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == "search_solr"
    assert result.tool_calls[0].arguments == {"collection": "knowledge_base", "query": "PRD"}


def test_default_openrouter_model_is_priced():
    # An unpriced model trips BudgetGuard's fail-closed "unpriced model"
    # suspension after a single call (D-075), so the default must be priced.
    # Reads the declared default, not Settings(): a teammate's own .env may
    # point at another model, which must not make this test fail.
    from app.config import Settings

    assert Settings.model_fields["LLM_OPENROUTER_MODEL"].default in PRICING_TIERS
