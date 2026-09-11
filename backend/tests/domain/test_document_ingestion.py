from __future__ import annotations

import uuid

import pytest

from app.domain.documents.models import Document
from app.domain.documents.service import (
    MAX_UPLOAD_BYTES,
    DocumentIngestionService,
    DocumentNotFound,
    UploadRejected,
)

ORG = uuid.uuid4()
USER = uuid.uuid4()


class FakeRepo:
    def __init__(self, documents: list[Document] | None = None):
        self.documents = {d.id: d for d in (documents or [])}
        self.chunks: list = []
        self.deleted: list[uuid.UUID] = []

    async def create_document(self, document):
        self.documents[document.id] = document
        return document

    async def get_document_meta(self, document_id):
        return self.documents.get(document_id)

    async def list_documents(self, org_id):
        return [d for d in self.documents.values() if d.org_id == org_id]

    async def add_chunks(self, chunks):
        self.chunks.extend(chunks)

    async def delete_document(self, document_id):
        self.deleted.append(document_id)
        return self.documents.pop(document_id, None) is not None

    async def flush(self):
        pass


class FakeEmbeddings:
    dimensions = 768

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.batch_calls = 0

    async def embed(self, text):
        return [0.0] * self.dimensions

    async def embed_batch(self, texts):
        self.batch_calls += 1
        if self.fail:
            raise RuntimeError("embedding provider is down")
        return [[0.0] * self.dimensions for _ in texts]


def _service(repo=None, embeddings=None) -> DocumentIngestionService:
    return DocumentIngestionService(
        repo=repo or FakeRepo(), embedding_provider=embeddings or FakeEmbeddings()
    )


async def _upload(service, filename="apple-10k.pdf", size=1024, mime="application/pdf"):
    return await service.create_upload(
        org_id=ORG,
        uploaded_by=USER,
        filename=filename,
        mime_type=mime,
        size_bytes=size,
        access_scope=["public"],
    )


@pytest.mark.asyncio
async def test_upload_starts_pending_and_records_who_uploaded_it():
    service = _service()

    document = await _upload(service)

    assert document.status == "PENDING"
    assert document.uploaded_by == USER
    assert document.org_id == ORG
    assert document.source == "upload"


@pytest.mark.asyncio
async def test_the_title_is_derived_from_the_filename():
    """The title is what every citation displays, so '_10-K-2025-As-Filed.pdf'
    must not be what a reader sees."""
    service = _service()

    document = await _upload(service, filename="_10-K-2025-As-Filed.pdf")

    assert document.title == "10 K 2025 As Filed"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,size",
    [("notes.docx", 1024), ("deck.pptx", 1024), ("scan.png", 1024)],
)
async def test_unsupported_types_are_refused_before_a_row_exists(filename, size):
    """Told at upload time, not minutes later via a FAILED row."""
    repo = FakeRepo()
    service = _service(repo)

    with pytest.raises(UploadRejected):
        await _upload(service, filename=filename, size=size)

    assert repo.documents == {}


@pytest.mark.asyncio
async def test_an_empty_file_is_refused():
    with pytest.raises(UploadRejected):
        await _upload(_service(), size=0)


@pytest.mark.asyncio
async def test_an_oversized_file_is_refused_with_the_limit_in_the_message():
    with pytest.raises(UploadRejected) as exc:
        await _upload(_service(), size=MAX_UPLOAD_BYTES + 1)

    assert "limit" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_upload_is_refused_when_there_is_no_embedding_provider():
    """Accepting a file that could never be searched is worse than refusing."""
    service = DocumentIngestionService(repo=FakeRepo(), embedding_provider=None)

    with pytest.raises(UploadRejected):
        await _upload(service)


@pytest.mark.asyncio
async def test_ingestion_stores_page_numbered_chunks_and_marks_ready(monkeypatch):
    repo = FakeRepo()
    embeddings = FakeEmbeddings()
    service = _service(repo, embeddings)
    document = await _upload(service)

    monkeypatch.setattr(
        "app.domain.documents.service.extract",
        lambda data, filename, mime: [
            _page(1, "alpha beta gamma"),
            _page(2, "delta epsilon zeta"),
        ],
    )

    await service.ingest(document.id, b"pdf-bytes")

    assert document.status == "READY"
    assert document.error is None
    assert document.page_count == 2
    assert document.chunk_count == 2
    assert [c.page_number for c in repo.chunks] == [1, 2]
    # One batched call, not one call per chunk: a 150-chunk filing against a
    # shared per-minute quota is the difference between minutes and hours.
    assert embeddings.batch_calls == 1


@pytest.mark.asyncio
async def test_a_pdf_with_no_extractable_text_fails_with_an_actionable_message(monkeypatch):
    """The scanned-document case. It must say so rather than fail silently."""
    repo = FakeRepo()
    service = _service(repo)
    document = await _upload(service)

    monkeypatch.setattr("app.domain.documents.service.extract", lambda *a: [])

    await service.ingest(document.id, b"pdf-bytes")

    assert document.status == "FAILED"
    assert "ocr" in (document.error or "").lower()
    assert repo.chunks == []


@pytest.mark.asyncio
async def test_a_failing_embedding_provider_marks_failed_rather_than_raising(monkeypatch):
    """Nothing awaits ingestion, so a raise would leave the row PROCESSING
    forever while the console polls a status that never changes."""
    repo = FakeRepo()
    service = _service(repo, FakeEmbeddings(fail=True))
    document = await _upload(service)

    monkeypatch.setattr(
        "app.domain.documents.service.extract", lambda *a: [_page(1, "alpha beta")]
    )

    await service.ingest(document.id, b"pdf-bytes")

    assert document.status == "FAILED"
    assert "down" in document.error


@pytest.mark.asyncio
async def test_ingesting_a_document_that_vanished_is_not_an_error():
    await _service().ingest(uuid.uuid4(), b"pdf-bytes")


@pytest.mark.asyncio
async def test_another_orgs_document_reads_as_missing_not_forbidden():
    """403 would confirm the id exists."""
    document = Document(
        id=uuid.uuid4(), org_id=uuid.uuid4(), title="Theirs", source="upload",
        access_scope=["public"], status="READY",
    )
    service = _service(FakeRepo([document]))

    with pytest.raises(DocumentNotFound):
        await service.get_document(document.id, org_id=ORG)


@pytest.mark.asyncio
async def test_deleting_another_orgs_document_is_refused():
    document = Document(
        id=uuid.uuid4(), org_id=uuid.uuid4(), title="Theirs", source="upload",
        access_scope=["public"], status="READY",
    )
    repo = FakeRepo([document])
    service = _service(repo)

    with pytest.raises(DocumentNotFound):
        await service.delete_document(document.id, org_id=ORG)

    assert repo.deleted == []


def _page(number: int, text: str):
    from app.runtime.rag.extractors import ExtractedPage

    return ExtractedPage(page_number=number, text=text)
