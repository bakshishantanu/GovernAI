from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _chunk_text(text: str, chunk_size_words: int, overlap_words: int) -> list[str]:
    """Fixed-size chunking with overlap (FRD-08: ~512 tokens/50-token overlap
    in the real pipeline; word-based here since MVP seed docs are short)."""
    words = text.split()
    if not words:
        return []

    chunks = []
    step = max(chunk_size_words - overlap_words, 1)
    start = 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + chunk_size_words]))
        if start + chunk_size_words >= len(words):
            break
        start += step
    return chunks


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    access_scope: frozenset[str]


@dataclass(frozen=True)
class DocumentChunk:
    document_id: str
    document_title: str
    chunk_index: int
    text: str

    @property
    def chunk_id(self) -> str:
        return f"{self.document_id}#{self.chunk_index}"


@dataclass(frozen=True)
class SearchResult:
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    text: str
    relevance_score: float


class _TfidfIndex:
    """Pure-Python TF-IDF + cosine similarity. IDF is computed once, over the
    whole corpus, at index build time - a corpus-wide vocabulary statistic,
    not a per-query leak of restricted content (only permitted chunks are
    ever scored/returned per query - see DocumentSearchAdapter.search)."""

    def __init__(self, chunk_tokens: dict[str, list[str]]):
        self._chunk_tokens = chunk_tokens
        self._idf = self._compute_idf(chunk_tokens)
        self._chunk_vectors = {cid: self._vector(tokens) for cid, tokens in chunk_tokens.items()}

    @staticmethod
    def _compute_idf(chunk_tokens: dict[str, list[str]]) -> dict[str, float]:
        n_chunks = len(chunk_tokens)
        doc_freq: Counter = Counter()
        for tokens in chunk_tokens.values():
            for term in set(tokens):
                doc_freq[term] += 1
        return {term: math.log((1 + n_chunks) / (1 + count)) + 1 for term, count in doc_freq.items()}

    def _vector(self, tokens: list[str]) -> dict[str, float]:
        tf = Counter(tokens)
        return {term: count * self._idf.get(term, 0.0) for term, count in tf.items()}

    def score(self, chunk_id: str, query_tokens: list[str]) -> float:
        query_vec = self._vector(query_tokens)
        chunk_vec = self._chunk_vectors[chunk_id]
        common = set(query_vec) & set(chunk_vec)
        numerator = sum(query_vec[t] * chunk_vec[t] for t in common)
        norm_q = math.sqrt(sum(v * v for v in query_vec.values()))
        norm_c = math.sqrt(sum(v * v for v in chunk_vec.values()))
        if norm_q == 0 or norm_c == 0:
            return 0.0
        return numerator / (norm_q * norm_c)


class DocumentSearchAdapter:
    """Mock, seeded document store (FRD-04: mock adapter behind a real
    interface). Enforces FRD-08's hard requirement: access-scope filtering
    happens BEFORE ranking, never after - a restricted chunk is never even
    scored, let alone returned.
    """

    def __init__(
        self,
        documents: list[tuple[Document, str]] | None = None,
        chunk_size_words: int = 80,
        chunk_overlap_words: int = 15,
        min_relevance_score: float = 0.05,
    ) -> None:
        docs_with_text = documents if documents is not None else _seed_documents()
        self._documents: dict[str, Document] = {doc.id: doc for doc, _ in docs_with_text}
        self._document_texts: dict[str, str] = {doc.id: text for doc, text in docs_with_text}
        self._min_relevance_score = min_relevance_score

        self._chunks: dict[str, DocumentChunk] = {}
        for doc, text in docs_with_text:
            for idx, chunk_text in enumerate(_chunk_text(text, chunk_size_words, chunk_overlap_words)):
                chunk = DocumentChunk(
                    document_id=doc.id, document_title=doc.title, chunk_index=idx, text=chunk_text
                )
                self._chunks[chunk.chunk_id] = chunk

        self._index = _TfidfIndex({cid: _tokenize(c.text) for cid, c in self._chunks.items()})

    def get_document(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def get_document_text(self, document_id: str) -> str | None:
        return self._document_texts.get(document_id)

    def search(self, query: str, permitted_scopes: frozenset[str], top_n: int = 3) -> list[SearchResult]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidate_ids = [
            cid
            for cid, chunk in self._chunks.items()
            if self._documents[chunk.document_id].access_scope & permitted_scopes
        ]

        scored = [(cid, self._index.score(cid, query_tokens)) for cid in candidate_ids]
        scored = [(cid, score) for cid, score in scored if score >= self._min_relevance_score]
        scored.sort(key=lambda pair: pair[1], reverse=True)

        results = []
        for cid, score in scored[:top_n]:
            chunk = self._chunks[cid]
            results.append(
                SearchResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=chunk.document_title,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    relevance_score=round(score, 4),
                )
            )
        return results


def _seed_documents() -> list[tuple[Document, str]]:
    return [
        (
            Document(id="DOC-1", title="GovernAI Onboarding Guide", access_scope=frozenset({"public"})),
            "GovernAI lets builders assemble AI agents from reusable skills. Every agent automatically "
            "receives an identity, a scoped permission set, and a live cost budget the moment it is "
            "created. Governance is generated at creation time, not configured afterward.",
        ),
        (
            Document(id="DOC-2", title="Policy Engine Overview", access_scope=frozenset({"public"})),
            "The Policy Engine evaluates every tool call an agent makes. It checks the agent's Passport, "
            "confirms the requested permission is granted, and applies any enabled policy rules such as "
            "deny lists and rate limits. If the Policy Engine fails for any reason, the call is denied - "
            "the system never fails open.",
        ),
        (
            Document(id="DOC-3", title="Cost Tracking FAQ", access_scope=frozenset({"public"})),
            "Every LLM call records prompt tokens, completion tokens, and a calculated cost in US dollars "
            "from a configurable pricing table. When an agent's accumulated cost meets its budget cap, "
            "the agent is automatically paused and the event is logged.",
        ),
        (
            Document(
                id="DOC-4", title="Internal Salary Bands", access_scope=frozenset({"hr_confidential"})
            ),
            "Engineering levels range from L3 to L7. L3 base salary starts at 12 lakh per annum, rising "
            "to 45 lakh at L7. This document is confidential and restricted to HR personnel only.",
        ),
        (
            Document(id="DOC-5", title="Kill Switch Runbook", access_scope=frozenset({"public"})),
            "Clicking Kill on the dashboard sets the agent's status to SUSPENDED in a single transaction. "
            "The next governance check for any running execution will then deny the call and the "
            "execution terminates gracefully within one tool-call cycle.",
        ),
    ]
