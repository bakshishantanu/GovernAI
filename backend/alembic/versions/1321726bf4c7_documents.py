"""documents

Revision ID: 1321726bf4c7
Revises: bd69854683f0
Create Date: 2026-08-31 13:24:42.599788

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1321726bf4c7'
down_revision: Union[str, Sequence[str], None] = 'bd69854683f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # Requires pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),
        sa.Column('access_scope', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('document_id', sa.UUID(), sa.ForeignKey('documents.id'), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        # Assuming 768 or 1536 depending on the model, we can leave dimension unspecified or use 768
        sa.Column('embedding', sa.text(), nullable=False), 
        sa.Column('chunk_index', sa.Integer(), nullable=False)
    )
    # Cast embedding string to vector type properly
    op.execute('ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector USING embedding::vector')
    op.execute('CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops)')
    
    op.execute('ALTER TABLE documents ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
