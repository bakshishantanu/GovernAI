import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.runtime.rag.pgvector_search import PgVectorDocumentSearchAdapter

_DOC_ID = uuid.uuid4()


def _chunk(
    text: str,
    embedding: list[float],
    index: int = 0,
    title: str = "Policy Engine Overview",
    page_number: int | None = None,
    locator: str | None = None,
):
    return SimpleNamespace(
        document_id=_DOC_ID,
        chunk_index=index,
        content=text,
        embedding=embedding,
        page_number=page_number,
        locator=locator,
        document=SimpleNamespace(title=title),
    )


def _repo(chunks: list) -> AsyncMock:
    repo = AsyncMock()
    repo.search_chunks_by_scope.return_value = chunks
    return repo


def _embeddings(vector: list[float]) -> AsyncMock:
    provider = AsyncMock()
    provider.embed.return_value = vector
    return provider


async def test_search_embeds_the_query_and_returns_scored_results():
    # identical vector -> cosine distance 0 -> relevance_score 1.0
    chunk = _chunk("the policy engine denies by default", embedding=[1.0, 0.0])
    repo = _repo([chunk])
    embeddings = _embeddings([1.0, 0.0])
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=embeddings)

    results = await adapter.search(
        "how does the policy engine work", permitted_scopes=frozenset({"public"})
    )

    assert len(results) == 1
    assert results[0].chunk_id == f"{_DOC_ID}#0"
    assert results[0].document_title == "Policy Engine Overview"
    assert results[0].relevance_score == 1.0


async def test_search_carries_the_locator_into_the_citation():
    """The location has to survive retrieval, or an answer cannot say where a
    fact came from - which is the whole reason chunks store one."""
    chunk = _chunk(
        "net sales rose", embedding=[1.0, 0.0], page_number=32, locator="p.32",
        title="Apple 10 K",
    )
    adapter = PgVectorDocumentSearchAdapter(
        repo=_repo([chunk]), embedding_provider=_embeddings([1.0, 0.0])
    )

    results = await adapter.search("net sales", permitted_scopes=frozenset({"public"}))

    assert results[0].page_number == 32
    assert results[0].citation == "Apple 10 K, p.32"


async def test_a_slide_is_cited_as_a_slide_not_a_page():
    """The locator wins over the number, so a deck does not claim to have
    pages it does not have."""
    chunk = _chunk(
        "BCNF removes the anomaly", embedding=[1.0, 0.0], page_number=7, locator="slide 7",
        title="Normalization Deck",
    )
    adapter = PgVectorDocumentSearchAdapter(
        repo=_repo([chunk]), embedding_provider=_embeddings([1.0, 0.0])
    )

    results = await adapter.search("BCNF", permitted_scopes=frozenset({"public"}))

    assert results[0].citation == "Normalization Deck, slide 7"


async def test_a_word_section_is_cited_by_heading_with_no_page():
    """A .docx stores no page numbers at all, so the heading is the only
    honest locator."""
    chunk = _chunk(
        "We compared ResNet50", embedding=[1.0, 0.0], locator="C. CNN Backbone Configuration",
        title="Monkeypox Paper",
    )
    adapter = PgVectorDocumentSearchAdapter(
        repo=_repo([chunk]), embedding_provider=_embeddings([1.0, 0.0])
    )

    results = await adapter.search("backbone", permitted_scopes=frozenset({"public"}))

    assert results[0].page_number is None
    assert results[0].citation == "Monkeypox Paper, C. CNN Backbone Configuration"


async def test_a_chunk_with_no_location_at_all_cites_by_title_alone():
    """Seeded demo documents have neither pages nor sections; inventing a
    position would produce a citation that cannot be looked up."""
    chunk = _chunk("governance at creation time", embedding=[1.0, 0.0], title="Onboarding Guide")
    adapter = PgVectorDocumentSearchAdapter(
        repo=_repo([chunk]), embedding_provider=_embeddings([1.0, 0.0])
    )

    results = await adapter.search("governance", permitted_scopes=frozenset({"public"}))

    assert results[0].page_number is None
    assert results[0].citation == "Onboarding Guide"


async def test_search_passes_permitted_scopes_and_embedding_to_the_repo():
    repo = _repo([])
    embeddings = _embeddings([1.0, 0.0])
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=embeddings)

    await adapter.search(
        "query", permitted_scopes=frozenset({"public", "hr_confidential"}), top_n=5
    )

    _, kwargs = repo.search_chunks_by_scope.call_args
    assert kwargs["embedding"] == [1.0, 0.0]
    assert sorted(kwargs["permitted_scopes"]) == ["hr_confidential", "public"]
    assert kwargs["limit"] == 5


async def test_search_filters_out_results_below_min_relevance_score():
    # orthogonal vectors -> cosine distance 1.0 -> relevance_score 0.0
    chunk = _chunk("unrelated content", embedding=[0.0, 1.0])
    repo = _repo([chunk])
    embeddings = _embeddings([1.0, 0.0])
    adapter = PgVectorDocumentSearchAdapter(
        repo=repo, embedding_provider=embeddings, min_relevance_score=0.3
    )

    results = await adapter.search("query", permitted_scopes=frozenset({"public"}))

    assert results == []


async def test_get_document_returns_none_when_not_found():
    repo = AsyncMock()
    repo.get_document.return_value = None
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=AsyncMock())

    result = await adapter.get_document(str(uuid.uuid4()))

    assert result is None


async def test_get_document_returns_document_with_access_scope():
    db_document = SimpleNamespace(id=_DOC_ID, title="Onboarding Guide", access_scope=["public"])
    repo = AsyncMock()
    repo.get_document.return_value = db_document
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=AsyncMock())

    result = await adapter.get_document(str(_DOC_ID))

    assert result.title == "Onboarding Guide"
    assert result.access_scope == frozenset({"public"})


async def test_get_document_text_joins_chunks_in_order():
    db_document = SimpleNamespace(
        id=_DOC_ID,
        chunks=[
            SimpleNamespace(chunk_index=1, content="second."),
            SimpleNamespace(chunk_index=0, content="first."),
        ],
    )
    repo = AsyncMock()
    repo.get_document.return_value = db_document
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=AsyncMock())

    text = await adapter.get_document_text(str(_DOC_ID))

    assert text == "first. second."


async def test_get_document_text_returns_none_when_not_found():
    repo = AsyncMock()
    repo.get_document.return_value = None
    adapter = PgVectorDocumentSearchAdapter(repo=repo, embedding_provider=AsyncMock())

    assert await adapter.get_document_text(str(uuid.uuid4())) is None
