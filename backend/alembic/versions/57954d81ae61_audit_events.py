"""audit_events

Revision ID: 57954d81ae61
Revises: e143d21637c4
Create Date: 2026-08-31 13:24:40.227102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '57954d81ae61'
down_revision: Union[str, Sequence[str], None] = 'e143d21637c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor_type', sa.String(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('agent_id', sa.UUID(), nullable=True),
        sa.Column('execution_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('resource', sa.String(), nullable=True),
        sa.Column('tool', sa.String(), nullable=True),
        sa.Column('policy_decision', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=True),
        sa.Column('reason', sa.String(), nullable=True),
        sa.Column('cost_usd', sa.Float(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True)
    )
    op.execute('ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY')
    # Optional: restricted role creation could go here, but usually requires superuser



def downgrade() -> None:
    pass # Implement as needed
