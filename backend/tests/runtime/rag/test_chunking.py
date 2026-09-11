from app.runtime.rag.chunking import chunk_pages
from app.runtime.rag.extractors import ExtractedPage


def _page(number: int, word_count: int) -> ExtractedPage:
    return ExtractedPage(page_number=number, text=" ".join(f"w{i}" for i in range(word_count)))


def test_a_chunk_never_spans_two_pages():
    """The reason the whole pipeline is page-aware: a chunk built from the end
    of one page and the start of the next could not be cited honestly."""
    chunks = chunk_pages([_page(1, 30), _page(2, 30)], chunk_words=100, overlap_words=10)

    assert [c.page_number for c in chunks] == [1, 2]
    assert all(len(c.text.split()) == 30 for c in chunks)


def test_a_long_page_splits_into_several_chunks_all_on_that_page():
    chunks = chunk_pages([_page(7, 250)], chunk_words=100, overlap_words=20)

    assert len(chunks) > 1
    assert {c.page_number for c in chunks} == {7}


def test_chunk_index_is_continuous_across_pages():
    """Index identifies a chunk within the document, not within its page, so
    it stays unique once page numbering restarts."""
    chunks = chunk_pages([_page(1, 150), _page(2, 150)], chunk_words=100, overlap_words=20)

    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_consecutive_chunks_on_a_page_overlap():
    """Overlap keeps a sentence that straddles a chunk boundary retrievable."""
    chunks = chunk_pages([_page(1, 200)], chunk_words=100, overlap_words=20)

    first_words = chunks[0].text.split()
    second_words = chunks[1].text.split()
    assert first_words[-20:] == second_words[:20]


def test_empty_pages_are_skipped_rather_than_stored_as_blank_chunks():
    chunks = chunk_pages([ExtractedPage(page_number=1, text="   "), _page(2, 10)])

    assert [c.page_number for c in chunks] == [2]


def test_no_pages_produces_no_chunks():
    assert chunk_pages([]) == []
