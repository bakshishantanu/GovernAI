from unittest.mock import AsyncMock, MagicMock

from app.domain.skills.models import SkillModel, SkillPermission, ToolModel
from app.domain.skills.registry import SkillRegistry


def _mock_session() -> AsyncMock:
    session = AsyncMock()
    session.add = MagicMock()  # real AsyncSession.add() is synchronous, not a coroutine
    return session


def _added(session, model_type):
    return [call.args[0] for call in session.add.call_args_list if isinstance(call.args[0], model_type)]


async def test_bootstrap_registers_all_three_mvp_skills_independently():
    """Regression test: a hardcoded 'ticketing' existence check previously
    meant every OTHER skill in the loop was silently skipped, even though
    it appeared in skills_to_register."""
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = None
    session = _mock_session()

    registry = SkillRegistry(skill_repo, session)
    await registry.bootstrap()

    checked_ids = [call.args[0] for call in skill_repo.get_skill.call_args_list]
    assert checked_ids == ["ticketing", "sql_query", "document_search"]

    added_ids = {s.id for s in _added(session, SkillModel)}
    assert added_ids == {"ticketing", "sql_query", "document_search"}


async def test_bootstrap_skips_only_the_skill_that_already_exists():
    async def get_skill(skill_id):
        return object() if skill_id == "ticketing" else None

    skill_repo = AsyncMock()
    skill_repo.get_skill.side_effect = get_skill
    session = _mock_session()

    registry = SkillRegistry(skill_repo, session)
    await registry.bootstrap()

    added_ids = {s.id for s in _added(session, SkillModel)}
    assert "ticketing" not in added_ids
    assert added_ids == {"sql_query", "document_search"}


async def test_bootstrap_persists_skill_level_permissions():
    """Regression test: SkillPermission rows were never created at all,
    despite the table existing specifically for this."""
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = None
    session = _mock_session()

    registry = SkillRegistry(skill_repo, session)
    await registry.bootstrap()

    added_permissions = {p.permission for p in _added(session, SkillPermission)}
    assert "ticket:read" in added_permissions
    assert "ticket:create" in added_permissions
    assert "sql:read:tickets" in added_permissions
    assert "docs:search:public" in added_permissions


async def test_bootstrap_persists_a_specific_required_permission_per_tool():
    """Regression test: required_permission was always '' for every tool,
    since no tool had ever actually set it (the attribute existed on
    BaseTool with an unset default, and nothing overrode it)."""
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = None
    session = _mock_session()

    registry = SkillRegistry(skill_repo, session)
    await registry.bootstrap()

    tools_by_name = {t.name: t for t in _added(session, ToolModel)}
    assert tools_by_name["read_ticket"].required_permission == "ticket:read"
    assert tools_by_name["search_tickets"].required_permission == "ticket:read"
    assert tools_by_name["create_ticket_reply"].required_permission == "ticket:create"
    assert tools_by_name["run_sql_query"].required_permission == "sql:read:internal_payroll,sql:read:tickets"
    assert tools_by_name["search_documents"].required_permission == "docs:search:public"
    assert tools_by_name["get_document"].required_permission == "docs:search:public"


def test_get_tools_resolves_bound_skill_ids_to_their_tools():
    registry = SkillRegistry(AsyncMock(), _mock_session())

    tools = registry.get_tools(["ticketing"])

    assert {t.name for t in tools} == {"read_ticket", "search_tickets", "create_ticket_reply"}


def test_get_tools_combines_multiple_bound_skills():
    registry = SkillRegistry(AsyncMock(), _mock_session())

    tools = registry.get_tools(["ticketing", "sql_query"])

    assert {t.name for t in tools} == {
        "read_ticket",
        "search_tickets",
        "create_ticket_reply",
        "run_sql_query",
    }


def test_get_tools_skips_an_unregistered_skill_id():
    """A skill can be unbound/deregistered after an agent was created with it --
    the agent should just lose that tool, not crash the whole run."""
    registry = SkillRegistry(AsyncMock(), _mock_session())

    tools = registry.get_tools(["ticketing", "not_a_real_skill"])

    assert {t.name for t in tools} == {"read_ticket", "search_tickets", "create_ticket_reply"}


def test_get_tools_returns_empty_list_for_no_bound_skills():
    registry = SkillRegistry(AsyncMock(), _mock_session())

    assert registry.get_tools([]) == []


def test_document_search_uses_tfidf_adapter_when_no_embedding_provider_given():
    from app.runtime.rag.retrieval import DocumentSearchAdapter

    registry = SkillRegistry(AsyncMock(), _mock_session())

    skill = registry._instances["document_search"]
    assert isinstance(skill._adapter, DocumentSearchAdapter)


def test_document_search_uses_pgvector_adapter_when_embedding_provider_given():
    from app.runtime.rag.pgvector_search import PgVectorDocumentSearchAdapter

    registry = SkillRegistry(AsyncMock(), _mock_session(), embedding_provider=AsyncMock())

    skill = registry._instances["document_search"]
    assert isinstance(skill._adapter, PgVectorDocumentSearchAdapter)
