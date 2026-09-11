"""Splits extracted pages into embeddable chunks that remember their page.

Chunks never span a page boundary. A chunk built from the end of page 8 and
the start of page 9 could not be cited honestly, and an answer citing the
wrong page is worse than one citing nothing, because it looks checkable and
isn't.

Size: ~400 words, ~50 overlap. FRD-08 specifies "~512 tokens / 50-token
overlap" for the real pipeline; 400 words is roughly 520 tokens of English
prose. The value that shipped before this (80 words) was chosen for the short
seeded demo documents and is much too small for real ones: a 60,000-word
filing produces about 900 eighty-word chunks, each needing its own embedding
API call, and each too small to hold a complete idea. Larger chunks both cost
far fewer calls and retrieve better on dense prose, because a whole paragraph
of context lands in one vector rather than being split across five.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.runtime.rag.extractors import ExtractedPage

DEFAULT_CHUNK_WORDS = 400
DEFAULT_OVERLAP_WORDS = 50


@dataclass(frozen=True)
class PagedChunk:
    text: str
    page_number: int
    #: Position across the whole document, not within the page, so it stays a
    #: stable identifier for a chunk even though pages restart numbering.
    chunk_index: int


def chunk_pages(
    pages: list[ExtractedPage],
    chunk_words: int = DEFAULT_CHUNK_WORDS,
    overlap_words: int = DEFAULT_OVERLAP_WORDS,
) -> list[PagedChunk]:
    """Fixed-size overlapping chunks, restarted at every page boundary."""
    if chunk_words <= 0:
        raise ValueError("chunk_words must be positive")
    step = max(chunk_words - overlap_words, 1)

    chunks: list[PagedChunk] = []
    index = 0
    for page in pages:
        words = page.text.split()
        if not words:
            continue
        start = 0
        while start < len(words):
            text = " ".join(words[start : start + chunk_words])
            chunks.append(
                PagedChunk(text=text, page_number=page.page_number, chunk_index=index)
            )
            index += 1
            if start + chunk_words >= len(words):
                break
            start += step
    return chunks
