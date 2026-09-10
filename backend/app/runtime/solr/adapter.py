from __future__ import annotations

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field

from app.runtime.solr.validator import SolrQueryResultSet


class SolrSearchTimeoutError(Exception):
    """Raised when a search exceeds its configured time limit."""


class SolrSearchError(Exception):
    """Raised on any non-timeout search failure."""


@dataclass
class _IndexedDoc:
    """Internal: a document with pre-computed term frequencies."""
    raw: dict
    tf: Counter  # term -> count across all text fields


class SolrAdapter:
    """Mock, in-memory full-text search backend for the Enterprise Search
    Skill (MVP).  Uses basic TF-IDF ranking — no external dependencies.

    A real adapter would make HTTP calls to a SolrCloud cluster.  This one
    follows the same mock-adapter pattern as TicketingSkill's
    MockTicketingAdapter and the old SqlDataAdapter, so a real backend can
    be swapped in without the skill's tools changing at all.
    """

    def __init__(
        self,
        seed_data: dict[str, list[dict]] | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        # collection_name -> list of _IndexedDoc
        self._collections: dict[str, list[_IndexedDoc]] = {}
        # collection_name -> {term -> document_frequency}
        self._df: dict[str, Counter] = {}
        if seed_data:
            for collection, docs in seed_data.items():
                self._index_collection(collection, docs)

    # -- Indexing (only called at construction / seed time) ----------------

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-zA-Z0-9]+", text.lower())

    def _index_collection(self, name: str, docs: list[dict]) -> None:
        indexed: list[_IndexedDoc] = []
        df: Counter = Counter()
        for doc in docs:
            # Combine all string fields for TF computation
            all_text = " ".join(
                str(v) for v in doc.values() if isinstance(v, str)
            )
            tokens = self._tokenize(all_text)
            tf = Counter(tokens)
            unique_terms = set(tokens)
            for term in unique_terms:
                df[term] += 1
            indexed.append(_IndexedDoc(raw=doc, tf=tf))
        self._collections[name] = indexed
        self._df[name] = df

    # -- Public API --------------------------------------------------------

    def get_collections(self) -> list[str]:
        return sorted(self._collections.keys())

    def search(
        self,
        collection: str,
        query: str,
        filters: list[str] | None = None,
        fields: list[str] | None = None,
        rows: int = 10,
        start: int = 0,
    ) -> SolrQueryResultSet:
        """Full-text search with TF-IDF ranking, optional filter queries,
        and optional field selection."""
        deadline = time.monotonic() + self._timeout_seconds

        if collection not in self._collections:
            raise SolrSearchError(f"collection '{collection}' does not exist")

        docs = self._collections[collection]
        df = self._df[collection]
        n_docs = len(docs)

        # Parse filter queries: "field:value" equality
        parsed_filters = self._parse_filters(filters or [])

        # Score every document
        query_tokens = self._tokenize(query)
        scored: list[tuple[float, dict]] = []

        for idoc in docs:
            if time.monotonic() > deadline:
                raise SolrSearchTimeoutError(
                    f"search exceeded the {self._timeout_seconds}s time limit"
                )

            # Apply filters
            if not self._matches_filters(idoc.raw, parsed_filters):
                continue

            # TF-IDF score
            score = 0.0
            for token in query_tokens:
                tf = idoc.tf.get(token, 0)
                doc_freq = df.get(token, 0)
                if tf > 0 and doc_freq > 0:
                    idf = math.log((n_docs + 1) / (doc_freq + 1)) + 1
                    score += tf * idf

            if score > 0:
                scored.append((score, idoc.raw))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        total_found = len(scored)

        # Paginate
        page = scored[start: start + rows]

        # Field selection
        documents = []
        for score, raw in page:
            doc = self._select_fields(raw, fields)
            doc["_score"] = round(score, 4)
            documents.append(doc)

        return SolrQueryResultSet(
            documents=documents,
            total_found=total_found,
        )

    def facet_search(
        self,
        collection: str,
        query: str,
        facet_fields: list[str],
        filters: list[str] | None = None,
    ) -> SolrQueryResultSet:
        """Search + facet counts for the specified fields."""
        deadline = time.monotonic() + self._timeout_seconds

        if collection not in self._collections:
            raise SolrSearchError(f"collection '{collection}' does not exist")

        docs = self._collections[collection]
        parsed_filters = self._parse_filters(filters or [])
        query_tokens = self._tokenize(query)

        # Collect matching docs + facet counts
        facet_counts: dict[str, Counter] = {f: Counter() for f in facet_fields}
        matched_docs: list[dict] = []

        for idoc in docs:
            if time.monotonic() > deadline:
                raise SolrSearchTimeoutError(
                    f"search exceeded the {self._timeout_seconds}s time limit"
                )

            if not self._matches_filters(idoc.raw, parsed_filters):
                continue

            # Check if doc matches query (score > 0) or query is "*:*" (match all)
            if query.strip() == "*:*" or any(idoc.tf.get(t, 0) > 0 for t in query_tokens):
                matched_docs.append(idoc.raw)
                for ff in facet_fields:
                    val = idoc.raw.get(ff, "")
                    if val:
                        facet_counts[ff][str(val)] += 1

        facets = {
            ff: dict(counts.most_common())
            for ff, counts in facet_counts.items()
        }

        return SolrQueryResultSet(
            documents=[],  # Facet queries return counts, not full docs
            total_found=len(matched_docs),
            facets=facets,
        )

    # -- Internal helpers --------------------------------------------------

    @staticmethod
    def _parse_filters(filters: list[str]) -> list[tuple[str, str]]:
        """Parse 'field:value' filter strings."""
        parsed = []
        for f in filters:
            if ":" in f:
                key, val = f.split(":", 1)
                parsed.append((key.strip(), val.strip()))
        return parsed

    @staticmethod
    def _matches_filters(doc: dict, filters: list[tuple[str, str]]) -> bool:
        for key, val in filters:
            doc_val = str(doc.get(key, "")).lower()
            if doc_val != val.lower():
                return False
        return True

    @staticmethod
    def _select_fields(doc: dict, fields: list[str] | None) -> dict:
        if not fields or "*" in fields:
            return dict(doc)
        return {k: v for k, v in doc.items() if k in fields}
