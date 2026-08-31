from app.runtime.rag.citations import extract_citation_ids, verify_answer_is_grounded


def test_extract_citation_ids_finds_all_markers():
    answer = "GovernAI uses a policy engine [DOC-2#0] and a cost cap [DOC-3#0]."
    assert extract_citation_ids(answer) == ["DOC-2#0", "DOC-3#0"]


def test_extract_citation_ids_returns_empty_when_none_present():
    assert extract_citation_ids("No citations here at all.") == []


def test_grounded_when_every_citation_was_actually_retrieved():
    answer = "The policy engine denies calls by default [DOC-2#0]."
    result = verify_answer_is_grounded(answer, retrieved_chunk_ids=["DOC-2#0", "DOC-1#0"])
    assert result["fully_grounded"] is True
    assert result["unsupported_citations"] == []


def test_not_grounded_when_a_citation_was_never_retrieved():
    """This is the actual hallucination-catching case: the model cited a
    chunk_id that was never in the retrieved set for this run."""
    answer = "Salaries range widely [DOC-4#0]."
    result = verify_answer_is_grounded(answer, retrieved_chunk_ids=["DOC-2#0"])
    assert result["fully_grounded"] is False
    assert result["unsupported_citations"] == ["DOC-4#0"]


def test_not_grounded_when_answer_has_no_citations_at_all():
    answer = "The policy engine denies calls by default."
    result = verify_answer_is_grounded(answer, retrieved_chunk_ids=["DOC-2#0"])
    assert result["has_citations"] is False
    assert result["fully_grounded"] is False
