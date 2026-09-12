from app.runtime.rag.retrieval import DocumentSearchAdapter
from app.skills.document_search import DocumentSearchSkill, SearchDocumentsTool


def test_skill_declares_per_scope_permissions():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    assert skill.required_permissions == ["docs:search:public"]


def test_skill_exposes_both_tools():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    names = {t.name for t in skill.get_tools()}
    assert names == {"search_documents", "get_document"}


async def test_search_returns_citable_grounded_results():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    tool = next(t for t in skill.get_tools() if t.name == "search_documents")

    result = await tool.execute(query="how does the policy engine work")

    assert result["found"] is True
    assert result["results"][0]["chunk_id"] == "DOC-2#0"
    assert "relevance_score" in result["results"][0]


async def test_search_reports_not_found_honestly_instead_of_fabricating():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    tool = next(t for t in skill.get_tools() if t.name == "search_documents")

    result = await tool.execute(query="banana spaceship guitar")

    assert result["found"] is False
    assert result["results"] == []
    assert "message" in result


async def test_search_at_tool_level_never_leaks_out_of_scope_content():
    adapter = DocumentSearchAdapter()
    public_skill = DocumentSearchSkill(permitted_scopes={"public"}, adapter=adapter)
    tool = next(t for t in public_skill.get_tools() if t.name == "search_documents")

    result = await tool.execute(query="engineering salary bands")

    assert all(r["document_id"] != "DOC-4" for r in result["results"])


async def test_get_document_denies_out_of_scope_document():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    tool = next(t for t in skill.get_tools() if t.name == "get_document")

    result = await tool.execute(document_id="DOC-4")

    assert result["found"] is False
    assert result["reason"] == "outside permitted scope"
    assert "full_text" not in result


async def test_get_document_returns_full_text_when_permitted():
    skill = DocumentSearchSkill(permitted_scopes={"hr_confidential"})
    tool = next(t for t in skill.get_tools() if t.name == "get_document")

    result = await tool.execute(document_id="DOC-4")

    assert result["found"] is True
    assert "salary" in result["full_text"].lower()


async def test_get_document_returns_not_found_for_unknown_id():
    skill = DocumentSearchSkill(permitted_scopes={"public"})
    tool = next(t for t in skill.get_tools() if t.name == "get_document")

    result = await tool.execute(document_id="DOC-999")

    assert result["found"] is False
    assert "reason" not in result


# --- Audit metadata: the "sources" panel's only data source ---------------


async def test_search_records_its_sources_for_the_audit_trail():
    """The run otherwise keeps no record of what retrieval returned: the
    governance layer hands the result to the model and drops it."""
    tool = SearchDocumentsTool(DocumentSearchAdapter(), frozenset({"public"}))
    arguments = {"query": "kill switch"}
    result = await tool.execute(**arguments)

    metadata = tool.audit_metadata(arguments, result)

    assert metadata["query"] == "kill switch"
    assert len(metadata["sources"]) >= 1
    source = metadata["sources"][0]
    assert source["citation"]
    assert source["chunk_id"]
    assert source["relevance_score"] > 0
    assert source["preview"]


async def test_a_search_that_found_nothing_is_still_recorded():
    """'The model answered anyway' and 'the model had nothing to go on' are
    different findings when reviewing a run."""
    tool = SearchDocumentsTool(DocumentSearchAdapter(), frozenset({"public"}))
    arguments = {"query": "zzzz-nonexistent-term-qqqq"}
    result = await tool.execute(**arguments)

    metadata = tool.audit_metadata(arguments, result)

    assert metadata == {"query": "zzzz-nonexistent-term-qqqq", "sources": []}


async def test_the_stored_preview_is_bounded_and_flags_truncation():
    """The full chunk is already in document_chunks and addressable by
    chunk_id; copying it into audit_events would duplicate the corpus."""
    from app.skills.document_search import _AUDIT_PREVIEW_CHARS

    tool = SearchDocumentsTool(None, frozenset({"public"}))
    long_text = "x" * (_AUDIT_PREVIEW_CHARS + 500)
    result = {
        "found": True,
        "results": [{"citation": "Doc, p.1", "chunk_id": "a#0", "text": long_text}],
    }

    metadata = tool.audit_metadata({"query": "q"}, result)

    assert len(metadata["sources"][0]["preview"]) == _AUDIT_PREVIEW_CHARS
    assert metadata["sources"][0]["truncated"] is True


async def test_a_tool_with_nothing_worth_auditing_records_nothing():
    """The default must stay None: a tool result can be large, and can hold
    content nobody decided should be copied into a second table."""
    from app.skills.document_search import GetDocumentTool

    tool = GetDocumentTool(None, frozenset({"public"}))

    assert tool.audit_metadata({"document_id": "x"}, {"found": True}) is None
