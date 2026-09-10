import pytest

from app.runtime.solr.adapter import SolrAdapter, SolrSearchError, SolrSearchTimeoutError

_SEED_DATA = {
    "knowledge_base": [
        {"id": "KB-1", "title": "Reset password", "content": "Visit IT portal to reset password", "department": "IT"},
        {"id": "KB-2", "title": "VPN connection", "content": "Connect to corporate VPN", "department": "IT"},
        {"id": "KB-3", "title": "Leave request", "content": "Submit PTO via HR portal", "department": "HR"},
    ],
    "confidential_hr": [
        {"id": "HR-1", "title": "Compensation", "content": "Salary bands for executives", "department": "HR"},
    ],
}


@pytest.fixture
def adapter():
    return SolrAdapter(seed_data=_SEED_DATA, timeout_seconds=10.0)


def test_seeded_data_is_queryable(adapter):
    result = adapter.search(collection="knowledge_base", query="password")
    assert result.total_found >= 1
    assert result.documents[0]["id"] == "KB-1"
    assert "_score" in result.documents[0]


def test_collections_reflects_seeded_data(adapter):
    assert adapter.get_collections() == ["confidential_hr", "knowledge_base"]


def test_empty_result_is_a_valid_success(adapter):
    result = adapter.search(collection="knowledge_base", query="nonexistentterm12345")
    assert result.total_found == 0
    assert result.documents == []


def test_nonexistent_collection_raises_error(adapter):
    with pytest.raises(SolrSearchError, match="does not exist"):
        adapter.search(collection="nonexistent_collection", query="test")


def test_filter_queries(adapter):
    result = adapter.search(collection="knowledge_base", query="portal", filters=["department:IT"])
    assert result.total_found == 1
    assert result.documents[0]["id"] == "KB-1"


def test_facet_search(adapter):
    result = adapter.facet_search(collection="knowledge_base", query="*:*", facet_fields=["department"])
    assert result.total_found == 3
    assert result.facets["department"]["IT"] == 2
    assert result.facets["department"]["HR"] == 1


def test_field_selection(adapter):
    result = adapter.search(collection="knowledge_base", query="password", fields=["id", "title"])
    assert "id" in result.documents[0]
    assert "title" in result.documents[0]
    assert "content" not in result.documents[0]


def test_search_timeout():
    adapter = SolrAdapter(seed_data=_SEED_DATA, timeout_seconds=-1.0)
    with pytest.raises(SolrSearchTimeoutError):
        adapter.search(collection="knowledge_base", query="password")
