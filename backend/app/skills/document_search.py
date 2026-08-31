from app.runtime.rag.citations import CITATION_INSTRUCTIONS
from app.runtime.rag.retrieval import DocumentSearchAdapter
from app.skills.base import BaseSkill, BaseTool, TrustLevel


class SearchDocumentsTool(BaseTool):
    name = "search_documents"
    description = "Search internal documents for content relevant to a question. " + CITATION_INSTRUCTIONS
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "The search query."}},
        "required": ["query"],
    }

    def __init__(self, adapter: DocumentSearchAdapter, permitted_scopes: frozenset[str]) -> None:
        self._adapter = adapter
        self._permitted_scopes = permitted_scopes
        # Coarse-grained gate for the registry/governance middleware. Fine-grained,
        # per-document scope enforcement happens inside the adapter regardless -
        # this is metadata, not the actual security boundary.
        self.required_permission = ",".join(f"docs:search:{s}" for s in sorted(permitted_scopes))

    async def execute(self, **kwargs) -> dict:
        results = self._adapter.search(kwargs["query"], self._permitted_scopes)
        if not results:
            return {
                "found": False,
                "results": [],
                "message": "No relevant documents were found for this query within your permitted scope.",
            }
        return {
            "found": True,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "text": r.text,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ],
        }


class GetDocumentTool(BaseTool):
    name = "get_document"
    description = "Fetch a specific document's full text by ID (only within your permitted scope)."
    parameters = {
        "type": "object",
        "properties": {"document_id": {"type": "string"}},
        "required": ["document_id"],
    }

    def __init__(self, adapter: DocumentSearchAdapter, permitted_scopes: frozenset[str]) -> None:
        self._adapter = adapter
        self._permitted_scopes = permitted_scopes
        # Coarse-grained gate for the registry/governance middleware. Fine-grained,
        # per-document scope enforcement happens inside the adapter regardless -
        # this is metadata, not the actual security boundary.
        self.required_permission = ",".join(f"docs:search:{s}" for s in sorted(permitted_scopes))

    async def execute(self, **kwargs) -> dict:
        document_id = kwargs["document_id"]
        document = self._adapter.get_document(document_id)
        if document is None:
            return {"found": False, "document_id": document_id}
        if not (document.access_scope & self._permitted_scopes):
            return {"found": False, "document_id": document_id, "reason": "outside permitted scope"}
        return {
            "found": True,
            "id": document.id,
            "title": document.title,
            "full_text": self._adapter.get_document_text(document.id),
        }


class DocumentSearchSkill(BaseSkill):
    name = "document_search"
    display_name = "Document Search"
    description = (
        "Search internal documents and answer questions with citations, grounded only in retrieved content."
    )
    version = "1.0.0"
    trust_level = TrustLevel.VERIFIED

    def __init__(
        self,
        permitted_scopes: set[str] | frozenset[str],
        adapter: DocumentSearchAdapter | None = None,
    ) -> None:
        self._permitted_scopes = frozenset(permitted_scopes)
        self._adapter = adapter or DocumentSearchAdapter()
        self.required_permissions = [f"docs:search:{scope}" for scope in sorted(self._permitted_scopes)]

    def get_tools(self) -> list[BaseTool]:
        return [
            SearchDocumentsTool(self._adapter, self._permitted_scopes),
            GetDocumentTool(self._adapter, self._permitted_scopes),
        ]
