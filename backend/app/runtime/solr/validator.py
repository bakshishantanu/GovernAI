from __future__ import annotations

from dataclasses import dataclass, field

# Maximum number of result rows a single query can request.
_MAX_ROWS = 100

# Substrings that must never appear in a query string passed to Solr.
# These are Solr admin/update endpoints or Lucene script injection vectors.
_FORBIDDEN_FRAGMENTS = ("/update", "/admin", "/replication", "/debug", "_val_:", "{!")


@dataclass(frozen=True)
class SolrQueryRequest:
    """The input to validation: an LLM-generated candidate Solr query plus
    the calling agent's permitted collection and field scope.  `query_string`
    is always untrusted (Constitution Principle 7 / FR-009 equivalent)."""

    question: str
    query_string: str
    collection: str
    permitted_collections: frozenset[str]
    permitted_fields: frozenset[str] | None = None  # None = all fields allowed
    requested_fields: list[str] = field(default_factory=list)
    rows: int = 10


@dataclass(frozen=True)
class SolrQueryValidationResult:
    """The outcome of validating a candidate Solr query, before any search
    is attempted.  `allowed=False` on any out-of-scope collection, any
    disallowed field, any dangerous query fragment, or any row-limit
    violation — never a silent allow."""

    allowed: bool
    reason: str | None
    collection: str = ""
    query_type: str = "SEARCH"


@dataclass(frozen=True)
class SolrSearchResult:
    """A single document returned by a permitted search."""

    id: str
    score: float
    fields: dict


@dataclass(frozen=True)
class SolrQueryResultSet:
    """The successful result of a permitted search.  An empty `documents`
    list with `total_found=0` is a valid success, not a failure."""

    documents: list[dict]
    total_found: int
    facets: dict = field(default_factory=dict)


def validate_solr_query(request: SolrQueryRequest) -> SolrQueryValidationResult:
    """Validate a candidate Solr query.  Fail-closed: any scope violation,
    any forbidden fragment, or any row-limit breach results in denial."""

    # 1. Collection scope
    if request.collection not in request.permitted_collections:
        return SolrQueryValidationResult(
            allowed=False,
            reason=f"collection '{request.collection}' is outside permitted scope: "
                   f"{', '.join(sorted(request.permitted_collections))}",
            collection=request.collection,
        )

    # 2. Field scope (if field restrictions are configured)
    if request.permitted_fields is not None and request.requested_fields:
        out_of_scope = [
            f for f in request.requested_fields
            if f != "*" and f not in request.permitted_fields
        ]
        if out_of_scope:
            return SolrQueryValidationResult(
                allowed=False,
                reason=f"requested field(s) outside permitted scope: {', '.join(out_of_scope)}",
                collection=request.collection,
            )

    # 3. Forbidden query fragments (injection / admin endpoint abuse)
    query_lower = request.query_string.lower()
    for fragment in _FORBIDDEN_FRAGMENTS:
        if fragment.lower() in query_lower:
            return SolrQueryValidationResult(
                allowed=False,
                reason=f"query contains forbidden fragment: '{fragment}'",
                collection=request.collection,
            )

    # 4. Row limit
    if request.rows > _MAX_ROWS:
        return SolrQueryValidationResult(
            allowed=False,
            reason=f"requested row count ({request.rows}) exceeds maximum ({_MAX_ROWS})",
            collection=request.collection,
        )

    if request.rows < 1:
        return SolrQueryValidationResult(
            allowed=False,
            reason="row count must be at least 1",
            collection=request.collection,
        )

    return SolrQueryValidationResult(
        allowed=True,
        reason=None,
        collection=request.collection,
    )
