"""organizations and profiles

Revision ID: b36db6e4a73e
Revises: a78b66a1b454
Create Date: 2026-08-31 13:24:33.233931

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b36db6e4a73e'
down_revision: Union[str, Sequence[str], None] = 'a78b66a1b454'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'organizations',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_table(
        'profiles',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.execute('ALTER TABLE organizations ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE profiles ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
