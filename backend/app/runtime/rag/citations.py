from __future__ import annotations

import re

#: A citation marker is whatever sits inside square brackets on one line.
#:
#: This used to be `\[([A-Za-z0-9\-]+#\d+)\]`, which only matched chunk ids
#: like "DOC-2#0". That was fine while documents were seeded mocks with
#: readable ids, but once documents are uploaded their id is a UUID, so every
#: citation rendered as "[629348d6-e83f-4c4e-85e3-6714dbfc1a7b#0]" - accurate,
#: and useless to the person meant to check it. Citations are now the human
#: label built by `build_citation` ("Apple 10 K, p.32"), so the pattern has to
#: accept spaces, commas and dots. Chunk-id style still matches, which keeps
#: the TF-IDF path (no pages, no uploads) working unchanged.
_CITATION_RE = re.compile(r"\[([^\[\]\n]{1,160})\]")

CITATION_INSTRUCTIONS = (
    "Answer only using the returned chunks - never from outside them. After "
    "every fact, cite the chunk it came from by copying that chunk's "
    "`citation` value verbatim inside square brackets, e.g. [Apple 10 K, p.32]. "
    "Do not invent a citation, renumber them, or cite a chunk you were not "
    "given. If no relevant chunks were found, say so explicitly instead of "
    "answering."
)


def build_citation(document_title: str, page_number: int | None) -> str:
    """The label a reader sees, and the exact string the model is told to cite.

    Page numbers are 1-based and match what a PDF viewer shows, so a citation
    can be checked by opening the document and turning to that page. Documents
    with no page information (the seeded demo set, and anything retrieved
    through the TF-IDF adapter) cite by title alone rather than inventing a
    page that would not survive being looked up.
    """
    if page_number is None:
        return document_title
    return f"{document_title}, p.{page_number}"


def extract_citation_ids(answer: str) -> list[str]:
    """Every citation marker in the answer, in the order they appear."""
    return [match.strip() for match in _CITATION_RE.findall(answer)]


def verify_answer_is_grounded(answer: str, retrieved_chunk_ids: list[str]) -> dict:
    """Mechanically check an answer's citations against what was actually
    retrieved during the run. This cannot force an LLM to comply with
    CITATION_INSTRUCTIONS - it catches when it didn't, so a caller (e.g. the
    execution layer) can flag or reject an ungrounded answer rather than
    just trusting the model's own claim.

    `retrieved_chunk_ids` accepts whichever identifier the answer was told to
    cite: chunk ids for the TF-IDF path, `build_citation` labels for uploaded
    documents. Comparison is case-insensitive and whitespace-insensitive,
    because a model that writes "Apple 10 K, P.32" has cited the right page
    and failing it for capitalisation would be noise, not a finding.
    """
    cited = extract_citation_ids(answer)
    retrieved = {_normalize(c) for c in retrieved_chunk_ids}
    unsupported = [c for c in cited if _normalize(c) not in retrieved]
    return {
        "has_citations": len(cited) > 0,
        "cited_chunk_ids": cited,
        "unsupported_citations": unsupported,
        "fully_grounded": len(cited) > 0 and not unsupported,
    }


def _normalize(citation: str) -> str:
    return " ".join(citation.split()).casefold()
