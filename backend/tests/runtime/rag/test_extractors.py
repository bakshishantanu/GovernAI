import io

import pytest

from app.runtime.rag.extractors import (
    ExtractionFailed,
    UnsupportedFileType,
    detect_format,
    extract_pdf,
)


def test_detect_format_accepts_a_pdf_by_extension():
    assert detect_format("annual-report.pdf", "application/pdf") == "pdf"


def test_extension_wins_over_a_wrong_mime_type():
    """Browsers routinely send application/octet-stream for a PDF; rejecting
    on that alone would refuse valid uploads."""
    assert detect_format("report.PDF", "application/octet-stream") == "pdf"


def test_a_wrong_mime_type_cannot_smuggle_in_an_unsupported_extension():
    """The other direction of the same distrust: a .docx labelled
    application/pdf must still be refused, or it is accepted here and fails
    minutes later inside the extractor."""
    with pytest.raises(UnsupportedFileType):
        detect_format("notes.docx", "application/pdf")


def test_mime_type_is_used_when_the_filename_has_no_extension():
    assert detect_format("report", "application/pdf") == "pdf"


@pytest.mark.parametrize("filename", ["notes.docx", "deck.pptx", "photo.png", "data.csv"])
def test_unsupported_types_are_refused_by_name(filename):
    """These are the formats still to come. Until an extractor exists, an
    upload must be refused up front rather than accepted and failed later."""
    with pytest.raises(UnsupportedFileType):
        detect_format(filename, None)


def test_the_refusal_message_names_what_is_supported():
    with pytest.raises(UnsupportedFileType) as exc:
        detect_format("deck.pptx", None)
    assert ".pdf" in str(exc.value)


def test_a_file_that_is_not_a_pdf_reports_extraction_failure():
    with pytest.raises(ExtractionFailed):
        extract_pdf(b"this is plainly not a pdf")


def test_blank_pages_are_skipped_rather_than_stored_as_empty_chunks():
    """A page with no extractable text is almost always a scanned image.
    Storing it as an empty chunk would pollute retrieval."""
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)

    assert extract_pdf(buffer.getvalue()) == []
