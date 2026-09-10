import pytest

from app.runtime.solr.validator import SolrQueryRequest, validate_solr_query

PERMITTED = frozenset({"knowledge_base", "compliance_docs"})


def _request(
    query_string: str,
    collection: str = "knowledge_base",
    permitted_collections: frozenset[str] = PERMITTED,
    permitted_fields: frozenset[str] | None = None,
    requested_fields: list[str] | None = None,
    rows: int = 10,
) -> SolrQueryRequest:
    return SolrQueryRequest(
        question="n/a",
        query_string=query_string,
        collection=collection,
        permitted_collections=permitted_collections,
        permitted_fields=permitted_fields,
        requested_fields=requested_fields or [],
        rows=rows,
    )


def test_allows_permitted_collection():
    result = validate_solr_query(_request("password reset", collection="knowledge_base"))
    assert result.allowed is True
    assert result.reason is None
    assert result.collection == "knowledge_base"


def test_denies_out_of_scope_collection():
    result = validate_solr_query(_request("exec compensation", collection="confidential_hr"))
    assert result.allowed is False
    assert "outside permitted scope" in result.reason
    assert "confidential_hr" in result.reason


@pytest.mark.parametrize(
    "forbidden",
    [
        "/update",
        "/admin",
        "/replication",
        "/debug",
        "_val_:",
        "{!lucene}",
    ],
)
def test_denies_forbidden_fragments(forbidden):
    result = validate_solr_query(_request(f"search term {forbidden} more"))
    assert result.allowed is False
    assert "forbidden fragment" in result.reason


def test_allows_permitted_fields():
    result = validate_solr_query(
        _request(
            "test",
            permitted_fields=frozenset({"title", "content"}),
            requested_fields=["title"],
        )
    )
    assert result.allowed is True


def test_denies_disallowed_fields():
    result = validate_solr_query(
        _request(
            "test",
            permitted_fields=frozenset({"title"}),
            requested_fields=["salary"],
        )
    )
    assert result.allowed is False
    assert "outside permitted scope" in result.reason


def test_row_limit_enforcement():
    result_too_many = validate_solr_query(_request("test", rows=101))
    assert result_too_many.allowed is False
    assert "exceeds maximum" in result_too_many.reason

    result_zero = validate_solr_query(_request("test", rows=0))
    assert result_zero.allowed is False
    assert "at least 1" in result_zero.reason
