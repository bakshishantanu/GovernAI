import pytest

from app.runtime.solr.adapter import SolrAdapter
from app.skills.solr_search import SearchSolrTool, FacetSolrTool, SolrSearchSkill

_SEED = {
    "knowledge_base": [
        {"id": "KB-001", "title": "Password Reset", "content": "Reset your password via the IT portal.", "department": "IT", "classification": "public"},
        {"id": "KB-002", "title": "VPN Setup", "content": "Download the VPN client from Software Center.", "department": "IT", "classification": "public"},
        {"id": "KB-003", "title": "Leave Policy", "content": "Employees receive 20 days annual leave.", "department": "HR", "classification": "public"},
    ],
    "confidential_hr": [
        {"id": "HR-001", "title": "Exec Compensation", "content": "CEO salary range 450K-600K.", "department": "HR", "classification": "restricted"},
    ],
}


@pytest.fixture
def adapter():
    return SolrAdapter(seed_data=_SEED)


@pytest.fixture
def skill(adapter):
    return SolrSearchSkill(
        permitted_collections={"knowledge_base"},
        adapter=adapter,
    )


# --- Skill metadata ---

def test_skill_declares_per_collection_permissions(skill):
    assert skill.required_permissions == ["solr:search:knowledge_base"]


def test_skill_exposes_search_and_facet_tools(skill):
    tools = skill.get_tools()
    assert len(tools) == 2
    names = {t.name for t in tools}
    assert names == {"search_solr", "facet_solr"}


# --- Successful search ---

async def test_search_permitted_collection_returns_results(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(
        question="how do I reset my password?",
        query="password reset",
        collection="knowledge_base",
    )
    assert result["success"] is True
    assert result["total_found"] >= 1
    assert any("KB-001" in str(d.get("id", "")) for d in result["documents"])


async def test_empty_result_is_success_not_denial(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(
        question="quantum physics",
        query="quantum entanglement superposition",
        collection="knowledge_base",
    )
    assert result["success"] is True
    assert result["total_found"] == 0
    assert result["documents"] == []


# --- Denied: out-of-scope collection ---

class _NeverCallAdapter:
    """Fails the test loudly if search() is ever called."""
    def search(self, **kwargs):
        raise AssertionError("adapter.search() should never be called for a denied query")
    def facet_search(self, **kwargs):
        raise AssertionError("adapter.facet_search() should never be called for a denied query")


async def test_out_of_scope_collection_denied_and_never_reaches_adapter():
    tool = SearchSolrTool(
        _NeverCallAdapter(),
        frozenset({"knowledge_base"}),
    )
    result = await tool.execute(
        question="show exec compensation",
        query="compensation salary",
        collection="confidential_hr",
    )
    assert result["success"] is False
    assert result["error"] == "denied"
    assert "confidential_hr" in result["reason"]


async def test_facet_out_of_scope_collection_denied():
    tool = FacetSolrTool(
        _NeverCallAdapter(),
        frozenset({"knowledge_base"}),
    )
    result = await tool.execute(
        collection="confidential_hr",
        query="*:*",
        facet_fields=["department"],
    )
    assert result["success"] is False
    assert result["error"] == "denied"


# --- Forbidden query fragments ---

async def test_forbidden_fragment_denied(skill):
    tool = skill.get_tools()[0]
    result = await tool.execute(
        question="hack attempt",
        query="{!lucene}password",
        collection="knowledge_base",
    )
    assert result["success"] is False
    assert result["error"] == "denied"
    assert "forbidden" in result["reason"].lower()


# --- Facet search ---

async def test_facet_returns_counts(skill):
    tools = {t.name: t for t in skill.get_tools()}
    result = await tools["facet_solr"].execute(
        collection="knowledge_base",
        query="*:*",
        facet_fields=["department"],
    )
    assert result["success"] is True
    assert "department" in result["facets"]
    assert result["facets"]["department"]["IT"] >= 1


# --- No internal details leak ---

async def test_no_internal_paths_leak_in_output(skill):
    tool = skill.get_tools()[0]
    outputs = [
        await tool.execute(question="ok", query="password", collection="knowledge_base"),
        await tool.execute(question="denied", query="salary", collection="confidential_hr"),
    ]
    for output in outputs:
        serialized = str(output)
        assert "solr_adapter" not in serialized.lower()
        assert "traceback" not in serialized.lower()
