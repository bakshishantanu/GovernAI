"""execution_triggered_by

Revision ID: 7a6f7b844de2
Revises: d7c3a1f0be21
Create Date: 2026-09-10

Required for this to run without error: the `Execution` ORM model declares
`triggered_by_id`, so any query touching it 500s without this column, not
just a missing feature.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a6f7b844de2'
down_revision: Union[str, Sequence[str], None] = 'd7c3a1f0be21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Nullable so every existing execution row is unaffected -- there is no
    way to backfill who triggered a past run, and this is not a fact worth
    guessing at. New runs started through POST /executions/ set it to the
    calling user's id; the Jira webhook (which has no human actor) leaves it
    null on purpose."""
    op.add_column(
        'executions',
        sa.Column('triggered_by_id', sa.UUID(), sa.ForeignKey('profiles.id'), nullable=True),
    )
    op.create_index('ix_executions_triggered_by_id', 'executions', ['triggered_by_id'])


def downgrade() -> None:
    op.drop_index('ix_executions_triggered_by_id', table_name='executions')
    op.drop_column('executions', 'triggered_by_id')
