"""A human-readable locator on each chunk, alongside the numeric page.

`page_number` alone cannot describe where a fact came from in every format:

  * A PDF has pages, so "p.32" is right.
  * A PPTX has slides. Citing "p.7" for slide 7 is simply wrong.
  * A DOCX has neither. Pages are produced by whatever renders the file, not
    stored in it, so any page number for a Word document would be invented.
    The honest locator there is the section heading the text sits under.

So the chunk stores the rendered locator string ("p.32", "slide 7",
"3.2 Convolutional Architectures") and keeps `page_number` for the formats
that genuinely have one, where it stays useful for ordering and for linking
straight to a page in a viewer.

Nullable: the seeded demo documents have no location of any kind, and citing
them by title alone is the truthful outcome.

Revision ID: c2f8a45d7e19
Revises: a7d3e91c4b58
Create Date: 2026-09-12
"""

from alembic import op
import sqlalchemy as sa

revision = "c2f8a45d7e19"
down_revision = "a7d3e91c4b58"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document_chunks", sa.Column("locator", sa.String(), nullable=True))
    # Backfill the PDFs ingested before this column existed, so their
    # citations keep naming a page rather than silently degrading to title only.
    op.execute(
        "UPDATE document_chunks SET locator = 'p.' || page_number "
        "WHERE page_number IS NOT NULL AND locator IS NULL"
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "locator")
