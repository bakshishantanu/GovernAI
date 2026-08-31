from app.runtime.rag.retrieval import DocumentSearchAdapter, _chunk_text


def test_search_returns_the_most_relevant_document_first():
    adapter = DocumentSearchAdapter()
    results = adapter.search("policy engine deny rules", permitted_scopes=frozenset({"public"}))
    assert results
    assert results[0].document_id == "DOC-2"
    assert results[0].document_title == "Policy Engine Overview"


def test_search_never_surfaces_out_of_scope_content_even_when_highly_relevant():
    """The confidential salary doc is the ONLY doc mentioning 'salary' - if
    prefiltering were broken (post-filtered instead), this exact query
    would leak it despite the agent lacking hr_confidential scope."""
    adapter = DocumentSearchAdapter()
    results = adapter.search("engineering salary bands", permitted_scopes=frozenset({"public"}))
    assert all(r.document_id != "DOC-4" for r in results)


def test_search_finds_confidential_doc_when_scope_is_granted():
    adapter = DocumentSearchAdapter()
    results = adapter.search("engineering salary bands", permitted_scopes=frozenset({"hr_confidential"}))
    assert any(r.document_id == "DOC-4" for r in results)


def test_search_with_no_permitted_scopes_returns_nothing():
    adapter = DocumentSearchAdapter()
    results = adapter.search("policy engine", permitted_scopes=frozenset())
    assert results == []


def test_search_returns_empty_for_query_with_no_term_overlap():
    adapter = DocumentSearchAdapter()
    results = adapter.search("banana spaceship guitar", permitted_scopes=frozenset({"public"}))
    assert results == []


def test_get_document_returns_none_for_unknown_id():
    adapter = DocumentSearchAdapter()
    assert adapter.get_document("DOC-999") is None


def test_get_document_text_returns_full_original_text():
    adapter = DocumentSearchAdapter()
    text = adapter.get_document_text("DOC-1")
    assert text is not None
    assert "reusable skills" in text


# --- chunking ---


def test_chunk_text_produces_overlapping_windows():
    text = " ".join(f"word{i}" for i in range(20))
    chunks = _chunk_text(text, chunk_size_words=10, overlap_words=3)
    assert len(chunks) >= 2
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert first_words[-3:] == second_words[:3]  # the overlapping window matches


def test_chunk_text_handles_short_text_as_a_single_chunk():
    chunks = _chunk_text("just a few words here", chunk_size_words=80, overlap_words=15)
    assert len(chunks) == 1


def test_chunk_text_handles_empty_text():
    assert _chunk_text("", chunk_size_words=80, overlap_words=15) == []
