from __future__ import annotations

from app.runtime.rag.citations import CITATION_INSTRUCTIONS
from app.runtime.rag.retrieval import DocumentRetriever, DocumentSearchAdapter
from app.skills.base import BaseSkill, BaseTool, TrustLevel

#: Per-source snippet kept on the audit record. Enough to recognise the
#: passage without copying the corpus into audit_events: the full chunk is
#: still in document_chunks, addressable by chunk_id.
_AUDIT_PREVIEW_CHARS = 320

#: Retrieval returns top_n=3 today, but a future caller could ask for more,
#: and an unbounded audit row is how a table becomes unusable.
_MAX_AUDITED_SOURCES = 10


class SearchDocumentsTool(BaseTool):
    name = "search_documents"
    description = (
        "Search internal documents for content relevant to a question. " + CITATION_INSTRUCTIONS
    )
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query."}},
        "required": ["query"],
    }

    def __init__(self, adapter: DocumentRetriever, permitted_scopes: frozenset[str]) -> None:
        self._adapter = adapter
        self._permitted_scopes = permitted_scopes
        # Coarse-grained gate for the registry/governance middleware. Fine-grained,
        # per-document scope enforcement happens inside the adapter regardless -
        # this is metadata, not the actual security boundary.
        self.required_permission = ",".join(f"docs:search:{s}" for s in sorted(permitted_scopes))

    async def execute(self, **kwargs) -> dict:
        results = await self._adapter.search(kwargs["query"], self._permitted_scopes)
        if not results:
            return {
                "found": False,
                "results": [],
                "message": (
                    "No relevant documents were found for this query within your permitted scope."
                ),
            }
        return {
            "found": True,
            "results": [
                {
                    # `citation` is what CITATION_INSTRUCTIONS tells the model
                    # to copy verbatim, so it is listed first and kept
                    # human-readable. chunk_id stays for callers that need to
                    # identify the exact chunk.
                    "citation": r.citation,
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "page_number": r.page_number,
                    "locator": r.locator,
                    "text": r.text,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ],
        }

    def audit_metadata(self, arguments: dict, result) -> dict | None:
        """Which chunks this search actually returned, for the run's record.

        "search_documents was ALLOWED" says nothing about whether the answer
        was grounded. The sources are the evidence, and nothing else on the
        run persists them: governance/middleware.py hands the result to the
        model and drops it.

        Stores a bounded preview rather than the whole chunk. The full text is
        already in document_chunks and is addressable by chunk_id, so copying
        it here would duplicate the corpus into the audit table for no gain.
        """
        if not isinstance(result, dict):
            return None
        if not result.get("found"):
            # A search that found nothing is still worth recording. "The model
            # answered anyway" and "the model had nothing to go on" are very
            # different findings when reviewing a run.
            return {"query": arguments.get("query"), "sources": []}

        sources = []
        for item in (result.get("results") or [])[:_MAX_AUDITED_SOURCES]:
            text = item.get("text") or ""
            sources.append(
                {
                    "citation": item.get("citation"),
                    "chunk_id": item.get("chunk_id"),
                    "document_id": item.get("document_id"),
                    "document_title": item.get("document_title"),
                    "page_number": item.get("page_number"),
                    "locator": item.get("locator"),
                    "relevance_score": item.get("relevance_score"),
                    "preview": text[:_AUDIT_PREVIEW_CHARS],
                    "truncated": len(text) > _AUDIT_PREVIEW_CHARS,
                }
            )
        return {"query": arguments.get("query"), "sources": sources}


class GetDocumentTool(BaseTool):
    name = "get_document"
    description = "Fetch a specific document's full text by ID (only within your permitted scope)."
    parameters = {
        "type": "object",
        "properties": {"document_id": {"type": "string"}},
        "required": ["document_id"],
    }

    def __init__(self, adapter: DocumentRetriever, permitted_scopes: frozenset[str]) -> None:
        self._adapter = adapter
        self._permitted_scopes = permitted_scopes
        # Coarse-grained gate for the registry/governance middleware. Fine-grained,
        # per-document scope enforcement happens inside the adapter regardless -
        # this is metadata, not the actual security boundary.
        self.required_permission = ",".join(f"docs:search:{s}" for s in sorted(permitted_scopes))

    async def execute(self, **kwargs) -> dict:
        document_id = kwargs["document_id"]
        document = await self._adapter.get_document(document_id)
        if document is None:
            return {"found": False, "document_id": document_id}
        if not (document.access_scope & self._permitted_scopes):
            return {"found": False, "document_id": document_id, "reason": "outside permitted scope"}
        return {
            "found": True,
            "id": document.id,
            "title": document.title,
            "full_text": await self._adapter.get_document_text(document.id),
        }


class DocumentSearchSkill(BaseSkill):
    name = "document_search"
    display_name = "Document Search"
    description = (
        "Search internal documents and answer questions with citations, "
        "grounded only in retrieved content."
    )
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED

    def __init__(
        self,
        permitted_scopes: set[str] | frozenset[str],
        adapter: DocumentRetriever | None = None,
    ) -> None:
        self._permitted_scopes = frozenset(permitted_scopes)
        self._adapter = adapter or DocumentSearchAdapter()
        self.required_permissions = [
            f"docs:search:{scope}" for scope in sorted(self._permitted_scopes)
        ]

    def get_tools(self) -> list[BaseTool]:
        return [
            SearchDocumentsTool(self._adapter, self._permitted_scopes),
            GetDocumentTool(self._adapter, self._permitted_scopes),
        ]
