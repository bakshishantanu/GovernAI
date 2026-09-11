"""Turns an uploaded file into text, one entry per page.

Page-awareness is the point. A flat string would be easier to produce, but
then a citation can only say "chunk 47", which a reader cannot check. Keeping
the page boundary all the way through to `DocumentChunk.page_number` is what
lets an answer say "[Apple 10-K, p.32]".

PDF is the only format wired up here. DOCX, PPTX and scanned-image OCR are
deliberately left as separate extractors to add later: the hard parts (schema,
upload endpoint, background ingestion, citations) are format-agnostic and are
done once, here, so each new format is a small self-contained addition rather
than a rewrite.
"""

from __future__ import annotations

import io
from dataclasses import dataclass


class UnsupportedFileType(Exception):
    """The uploaded file is not a format we can extract text from."""


class ExtractionFailed(Exception):
    """The file is a supported type but could not be read (corrupt, encrypted)."""


@dataclass(frozen=True)
class ExtractedPage:
    #: 1-based, matching what a reader sees in a PDF viewer. Off-by-one here
    #: would make every citation subtly wrong, which is worse than no citation.
    page_number: int
    text: str


#: Only what an extractor exists for. Checked on upload so a user finds out
#: immediately, rather than after a background job has already accepted and
#: then failed on their file.
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
}

SUPPORTED_EXTENSIONS = {".pdf": "pdf"}


def detect_format(filename: str, mime_type: str | None) -> str:
    """Which extractor handles this file.

    The filename's extension is authoritative *whenever it has one*. The MIME
    type is only consulted for a file with no extension at all.

    That asymmetry is deliberate. The browser-supplied MIME type is not
    trustworthy in either direction: browsers send application/octet-stream
    for a perfectly good PDF, so a MIME-only check rejects valid uploads, and
    a .docx can arrive labelled application/pdf, so letting MIME override a
    real extension accepts a file no extractor can read. Trusting the
    extension first and only falling back when there is nothing to trust
    handles both.
    """
    lowered = filename.lower()
    _, dot, extension = lowered.rpartition(".")
    if dot:
        fmt = SUPPORTED_EXTENSIONS.get(f".{extension}")
        if fmt is not None:
            return fmt
        raise UnsupportedFileType(
            f"'{filename}' is not a supported document type. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )

    if mime_type and mime_type in SUPPORTED_MIME_TYPES:
        return SUPPORTED_MIME_TYPES[mime_type]
    raise UnsupportedFileType(
        f"'{filename}' is not a supported document type. Supported: "
        + ", ".join(sorted(SUPPORTED_EXTENSIONS))
    )


def extract_pdf(data: bytes) -> list[ExtractedPage]:
    """Text per page from a PDF, skipping pages that yield nothing.

    A page with no extractable text is almost always a scanned image. Those
    are skipped rather than stored as empty chunks, and the caller can tell
    the difference between "this PDF has no text at all" (every page empty,
    so it needs OCR) and "some pages are images".
    """
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
    except PdfReadError as exc:
        raise ExtractionFailed(f"Could not read the PDF: {exc}") from exc

    if reader.is_encrypted:
        # An empty-password decrypt succeeds for PDFs that are "protected"
        # only against editing, which is common for filings and reports.
        try:
            if reader.decrypt("") == 0:
                raise ExtractionFailed("This PDF is password protected.")
        except (NotImplementedError, PdfReadError) as exc:
            raise ExtractionFailed(f"This PDF is encrypted and could not be opened: {exc}") from exc

    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            # One unreadable page must not lose the other 119.
            continue
        if text.strip():
            pages.append(ExtractedPage(page_number=index, text=text))
    return pages


def extract(data: bytes, filename: str, mime_type: str | None = None) -> list[ExtractedPage]:
    """Text per page for any supported upload."""
    fmt = detect_format(filename, mime_type)
    if fmt == "pdf":
        return extract_pdf(data)
    raise UnsupportedFileType(f"No extractor for format '{fmt}'")
