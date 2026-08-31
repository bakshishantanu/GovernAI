"""cost_events

Revision ID: bd69854683f0
Revises: 57954d81ae61
Create Date: 2026-08-31 13:24:41.391573

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bd69854683f0'
down_revision: Union[str, Sequence[str], None] = '57954d81ae61'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'cost_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('execution_id', sa.UUID(), sa.ForeignKey('executions.id'), nullable=False),
        sa.Column('execution_step_id', sa.UUID(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('total_tokens', sa.Integer(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True)
    )
    op.execute('ALTER TABLE cost_events ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
