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
    """One addressable piece of a document: a page, a slide, or a section.

    Named for the PDF case it started as, but the unit varies by format, which
    is exactly why `locator` exists rather than every format pretending to
    have page numbers.
    """

    #: 1-based, matching what a reader sees in a viewer. Off-by-one here would
    #: make every citation subtly wrong, which is worse than no citation.
    #: None for formats with no such numbering (DOCX).
    page_number: int | None
    text: str
    #: How a citation should name this spot: "p.32", "slide 7", or a heading.
    #: Only the extractor knows what unit the format really has.
    locator: str | None = None


#: Only what an extractor exists for. Checked on upload so a user finds out
#: immediately, rather than after a background job has already accepted and
#: then failed on their file.
SUPPORTED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
}

SUPPORTED_EXTENSIONS = {".pdf": "pdf", ".docx": "docx", ".pptx": "pptx"}


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
            pages.append(ExtractedPage(page_number=index, text=text, locator=f"p.{index}"))
    return pages


#: Longest section heading kept in a citation. A full heading can run to a
#: whole sentence, and "[Paper, 3.2 A Very Long Heading That Runs On...]" in
#: the middle of a sentence is unreadable.
_MAX_HEADING_CHARS = 60

#: Above this many words, a fully bold paragraph is a bold *sentence*, not a
#: heading. Measured against a real paper: its headings ("1. Introduction",
#: "C. CNN Backbone Configuration") run 2 to 6 words, while its abstract is a
#: bold paragraph of 90+ words that must not become a section marker.
_MAX_HEADING_WORDS = 12


def _looks_like_heading(paragraph) -> bool:
    """Whether this paragraph starts a new section.

    Word's Heading styles are the clean signal, and real documents mostly do
    not use them. In the paper this was built against, all 81 paragraphs are
    style "Normal" and every heading is marked by bold alone, which is typical
    of anything written from a journal template or pasted together.

    So bold-and-short is accepted as a heading too. Both halves matter: bold
    alone would promote a bold abstract paragraph into a section heading,
    and short alone would promote every one-line list item.
    """
    text = (paragraph.text or "").strip()
    if not text:
        return False

    style = (paragraph.style.name or "") if paragraph.style is not None else ""
    if style.startswith("Heading") or style in {"Title", "Subtitle"}:
        return True

    if len(text.split()) > _MAX_HEADING_WORDS:
        return False

    runs = [r for r in paragraph.runs if (r.text or "").strip()]
    # `bold` is None when inherited rather than set, which is not the same as
    # True: requiring every run to be explicitly bold keeps mixed-emphasis
    # body text (a sentence with one bold word) out.
    return bool(runs) and all(r.bold for r in runs)


def extract_docx(data: bytes) -> list[ExtractedPage]:
    """Text per section from a Word document, keyed on its headings.

    A .docx stores no page numbers. Pages are produced by whatever renders the
    file, using the reader's paper size, margins and fonts, so any page number
    here would be invented and would not survive being looked up. The honest
    locator is the heading the text sits under, which is also what a reader
    would actually use to find it.

    Text before the first heading becomes one leading section with no locator,
    rather than being dropped.
    """
    try:
        import docx
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ExtractionFailed(f"Word support is not installed: {exc}") from exc

    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionFailed(f"Could not read the Word document: {exc}") from exc

    sections: list[ExtractedPage] = []
    heading: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            sections.append(ExtractedPage(page_number=None, text=text, locator=heading))
        buffer.clear()

    for paragraph in document.paragraphs:
        text = (paragraph.text or "").strip()
        if not text:
            continue
        if _looks_like_heading(paragraph):
            flush()
            heading = text[:_MAX_HEADING_CHARS].strip()
            # The heading is part of its own section's text: it is often the
            # most retrievable phrase in it.
            buffer.append(text)
            continue
        buffer.append(text)
    flush()

    # Tables hold a lot of a paper's substance (results, comparisons) and are
    # not in `paragraphs` at all, so they would be silently lost.
    for index, table in enumerate(document.tables, start=1):
        rows = []
        for row in table.rows:
            # Cell text carries hard line breaks from the original layout
            # ("Baseli\nne\nAccur\nacy"), which would otherwise be embedded as
            # broken words.
            cells = [" ".join(cell.text.split()) for cell in row.cells]
            joined = " | ".join(c for c in cells if c)
            if joined:
                rows.append(joined)
        body = "\n".join(rows).strip()
        if body:
            sections.append(
                ExtractedPage(page_number=None, text=body, locator=f"table {index}")
            )

    return sections


def extract_pptx(data: bytes) -> list[ExtractedPage]:
    """Text per slide, cited as "slide N" rather than "p.N".

    A deck's unit is the slide, and a reader asked to check "p.7" of a
    presentation has to translate. Speaker notes are included: they routinely
    carry the explanation the slide itself only gestures at.
    """
    try:
        from pptx import Presentation
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ExtractionFailed(f"PowerPoint support is not installed: {exc}") from exc

    try:
        presentation = Presentation(io.BytesIO(data))
    except Exception as exc:
        raise ExtractionFailed(f"Could not read the presentation: {exc}") from exc

    slides: list[ExtractedPage] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts: list[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                if text:
                    parts.append(text)
            # A table on a slide is usually the densest thing on it.
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = " | ".join(c.text.strip() for c in row.cells if c.text.strip())
                    if cells:
                        parts.append(cells)

        notes = ""
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            notes = slide.notes_slide.notes_text_frame.text.strip()
        if notes:
            parts.append(f"Speaker notes: {notes}")

        body = "\n".join(parts).strip()
        if body:
            slides.append(
                ExtractedPage(page_number=index, text=body, locator=f"slide {index}")
            )
    return slides


def extract(data: bytes, filename: str, mime_type: str | None = None) -> list[ExtractedPage]:
    """Text, split into citable pieces, for any supported upload."""
    fmt = detect_format(filename, mime_type)
    if fmt == "pdf":
        return extract_pdf(data)
    if fmt == "docx":
        return extract_docx(data)
    if fmt == "pptx":
        return extract_pptx(data)
    raise UnsupportedFileType(f"No extractor for format '{fmt}'")
