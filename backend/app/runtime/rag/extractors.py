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
import logging
from dataclasses import dataclass

from app.runtime.rag.ocr import OcrProvider

logger = logging.getLogger(__name__)


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
    "image/jpeg": "image",
    "image/png": "image",
    "image/webp": "image",
}

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".webp": "image",
}

#: What an image extension is sent to the OCR model as. The uploader's
#: declared MIME type is not trusted here for the same reason it is not
#: trusted in detect_format.
_IMAGE_MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

#: Rasterisation scale for OCR of a scanned PDF page. 2x renders a typical
#: A4 page at ~1190x1682, which is legible to the model without producing
#: needlessly large uploads.
_OCR_RENDER_SCALE = 2


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


async def extract_pdf(data: bytes, ocr: OcrProvider | None = None) -> list[ExtractedPage]:
    """Text per page from a PDF, falling back to OCR for pages that have none.

    A page with no extractable text is a scanned image. With an OCR provider
    those pages are rendered and transcribed; without one they are skipped,
    and a wholly scanned PDF then produces nothing, which the caller reports
    as needing OCR rather than as an empty document.

    The fallback is per page, not per document, because mixed files are
    common: a born-digital report with a scanned signature page, or a scanned
    document with a digitally generated cover.
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
    needs_ocr: list[int] = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            # One unreadable page must not lose the other 119.
            text = ""
        if text.strip():
            pages.append(ExtractedPage(page_number=index, text=text, locator=f"p.{index}"))
        elif ocr is not None:
            needs_ocr.append(index)

    if needs_ocr:
        pages.extend(await _ocr_pdf_pages(data, needs_ocr, ocr))
        # Re-sorted because OCR'd pages are appended after the text ones, and
        # a document whose chunks run 3, 7, 1, 2 would be chunked in the wrong
        # reading order.
        pages.sort(key=lambda p: p.page_number or 0)

    return pages


async def _ocr_pdf_pages(
    data: bytes, page_numbers: list[int], ocr: OcrProvider
) -> list[ExtractedPage]:
    """Render the given 1-based pages and transcribe each one.

    Sequential on purpose. These calls share a per-minute quota with
    embedding, and firing fifteen at once buys a 429 storm rather than speed.
    """
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ExtractionFailed(f"OCR support is not installed: {exc}") from exc

    document = pdfium.PdfDocument(io.BytesIO(data))
    out: list[ExtractedPage] = []
    for number in page_numbers:
        try:
            image = document[number - 1].render(scale=_OCR_RENDER_SCALE).to_pil()
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=85)
            text = await ocr.read(buffer.getvalue(), "image/jpeg")
        except Exception:
            # One page the model cannot read must not lose the rest of a
            # 15-page scan.
            logger.exception("OCR failed for page %s", number)
            continue
        if text.strip():
            out.append(ExtractedPage(page_number=number, text=text, locator=f"p.{number}"))
    return out


async def extract_image(
    data: bytes, filename: str, ocr: OcrProvider | None
) -> list[ExtractedPage]:
    """Transcribe a single image.

    No locator: one image is one place, so the document title alone already
    says where a quote came from, and "p.1" would add nothing a reader could
    use.
    """
    if ocr is None:
        raise ExtractionFailed(
            "This is an image, which needs OCR to read, and OCR is not "
            "configured on this server."
        )
    _, _, extension = filename.lower().rpartition(".")
    mime = _IMAGE_MIME_BY_EXTENSION.get(f".{extension}", "image/jpeg")
    text = await ocr.read(data, mime)
    if not text.strip():
        return []
    return [ExtractedPage(page_number=None, text=text, locator=None)]


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


async def extract(
    data: bytes,
    filename: str,
    mime_type: str | None = None,
    ocr: OcrProvider | None = None,
) -> list[ExtractedPage]:
    """Text, split into citable pieces, for any supported upload.

    Async because OCR is a network call. The office formats are pure CPU and
    gain nothing from it, but one signature for every format keeps the caller
    from having to know which is which.
    """
    fmt = detect_format(filename, mime_type)
    if fmt == "pdf":
        return await extract_pdf(data, ocr=ocr)
    if fmt == "docx":
        return extract_docx(data)
    if fmt == "pptx":
        return extract_pptx(data)
    if fmt == "image":
        return await extract_image(data, filename, ocr)
    raise UnsupportedFileType(f"No extractor for format '{fmt}'")
