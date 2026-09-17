"""skill_requirements and connections

Revision ID: 62592e6f3f43
Revises: e91a4c7d0f3b
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62592e6f3f43'
down_revision: Union[str, Sequence[str], None] = 'e91a4c7d0f3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'skill_requirements',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('skill_id', sa.String(), sa.ForeignKey('skills.id'), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False, server_default=''),
        sa.Column('fields', sa.JSON(), nullable=True),
    )

    op.create_table(
        'connections',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('requirement_key', sa.String(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('label', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='CONNECTED'),
        sa.Column('encrypted_secret', sa.String(), nullable=True),
        sa.Column('preview', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.UniqueConstraint('org_id', 'requirement_key', name='uq_connection_org_key'),
    )

    op.execute('ALTER TABLE skill_requirements ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE connections ENABLE ROW LEVEL SECURITY')


def downgrade() -> None:
    op.drop_table('connections')
    op.drop_table('skill_requirements')
