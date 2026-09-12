"""Page-aware chunks and upload metadata on documents.

Two things become possible with this migration:

1. A citation can name *where* a fact came from. `document_chunks.page_number`
   records the 1-based page (or slide) the chunk's text was extracted from, so
   an answer can say "[Apple 10-K, p.32]" instead of "[<uuid>#47]", which is
   what a reader actually needs in order to check the claim.

2. Uploading is no longer a developer-only operation. Documents gain the
   metadata an upload produces (filename, mime type, who uploaded it, page and
   chunk counts) plus an ingestion `status`, because extracting and embedding a
   120-page filing takes minutes and cannot happen inside the request.

Every added column is nullable, except `status` which carries a server default
of 'READY'. That is deliberate: the demo documents seeded by
scripts/ingest_documents.py were never uploaded by anyone and have no filename
or page of their own, and they are already fully embedded, so 'READY' is the
truthful value for them and no backfill is needed.

Revision ID: a7d3e91c4b58
Revises: e52e63e33395
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa

revision = "a7d3e91c4b58"
down_revision = "e52e63e33395"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("page_number", sa.Integer(), nullable=True))

    op.add_column("documents", sa.Column("filename", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("mime_type", sa.String(), nullable=True))
    op.add_column("documents", sa.Column("uploaded_by", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer(), nullable=True))
    op.add_column("documents", sa.Column("chunk_count", sa.Integer(), nullable=True))
    op.add_column(
        "documents",
        sa.Column("status", sa.String(), nullable=False, server_default=sa.text("'READY'")),
    )
    op.add_column("documents", sa.Column("error", sa.String(), nullable=True))

    # The console lists documents for one org, newest first, and polls that
    # list while an upload is still processing.
    op.create_index("ix_documents_org_created", "documents", ["org_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_documents_org_created", table_name="documents")
    op.drop_column("documents", "error")
    op.drop_column("documents", "status")
    op.drop_column("documents", "chunk_count")
    op.drop_column("documents", "page_count")
    op.drop_column("documents", "uploaded_by")
    op.drop_column("documents", "mime_type")
    op.drop_column("documents", "filename")
    op.drop_column("document_chunks", "page_number")
