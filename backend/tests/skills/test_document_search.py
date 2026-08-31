from app.runtime.rag.retrieval import DocumentSearchAdapter
from app.skills.document_search import DocumentSearchSkill


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
