from unittest.mock import AsyncMock, MagicMock

from app.runtime.rag.embeddings import GeminiEmbeddingProvider


def _mock_client(response_json: dict) -> AsyncMock:
    response = MagicMock()
    response.json.return_value = response_json
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    client.post.return_value = response
    return client


async def test_embed_returns_the_vector():
    client = _mock_client({"embedding": {"values": [0.1, 0.2, 0.3]}})
    provider = GeminiEmbeddingProvider(api_key="test-key", client=client)

    result = await provider.embed("hello world")

    assert result == [0.1, 0.2, 0.3]


async def test_embed_sends_api_key_header():
    client = _mock_client({"embedding": {"values": [0.0]}})
    provider = GeminiEmbeddingProvider(api_key="secret", client=client)

    await provider.embed("hi")

    _, kwargs = client.post.call_args
    assert kwargs["headers"]["x-goog-api-key"] == "secret"


async def test_embed_sends_text_and_output_dimensionality():
    client = _mock_client({"embedding": {"values": [0.0]}})
    provider = GeminiEmbeddingProvider(api_key="k", client=client)

    await provider.embed("find the ticket")

    _, kwargs = client.post.call_args
    assert kwargs["json"]["content"]["parts"][0]["text"] == "find the ticket"
    assert kwargs["json"]["outputDimensionality"] == 768


async def test_provider_declares_768_dimensions_to_match_the_pgvector_column():
    assert GeminiEmbeddingProvider.dimensions == 768
