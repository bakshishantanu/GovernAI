import re

_CITATION_RE = re.compile(r"\[([A-Za-z0-9\-]+#\d+)\]")

CITATION_INSTRUCTIONS = (
    "Answer only using the returned chunks - never from outside them. Cite every "
    "fact using its chunk_id in square brackets, e.g. [DOC-1#0]. If no relevant "
    "chunks were found, say so explicitly instead of answering."
)


def extract_citation_ids(answer: str) -> list[str]:
    return _CITATION_RE.findall(answer)


def verify_answer_is_grounded(answer: str, retrieved_chunk_ids: list[str]) -> dict:
    """Mechanically check an answer's citations against what was actually
    retrieved during the run. This cannot force an LLM to comply with
    CITATION_INSTRUCTIONS - it catches when it didn't, so a caller (e.g. the
    execution layer) can flag or reject an ungrounded answer rather than
    just trusting the model's own claim.
    """
    cited = extract_citation_ids(answer)
    retrieved = set(retrieved_chunk_ids)
    unsupported = [c for c in cited if c not in retrieved]
    return {
        "has_citations": len(cited) > 0,
        "cited_chunk_ids": cited,
        "unsupported_citations": unsupported,
        "fully_grounded": len(cited) > 0 and not unsupported,
    }
