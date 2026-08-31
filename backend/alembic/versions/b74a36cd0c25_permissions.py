"""permissions

Revision ID: b74a36cd0c25
Revises: ecf18fd4ca20
Create Date: 2026-08-31 13:24:36.653418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b74a36cd0c25'
down_revision: Union[str, Sequence[str], None] = 'ecf18fd4ca20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('passport_id', sa.UUID(), sa.ForeignKey('agent_passports.id'), nullable=False),
        sa.Column('permission', sa.String(), nullable=False)
    )
    op.create_index('ix_permissions_passport', 'permissions', ['passport_id'])
    op.execute('ALTER TABLE permissions ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
