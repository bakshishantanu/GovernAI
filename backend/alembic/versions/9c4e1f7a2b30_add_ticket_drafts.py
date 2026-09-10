"""add ticket_drafts

Revision ID: 9c4e1f7a2b30
Revises: 7a1b2c3d4e5f
Create Date: 2026-09-10 18:40:00.000000

Replies an agent composes are parked here for a human to approve before
anything is written back to the ticketing backend.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '9c4e1f7a2b30'
down_revision: Union[str, Sequence[str], None] = '7a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ticket_drafts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('executions.id'), nullable=True),
        sa.Column('ticket_id', sa.String(64), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(20), server_default='PENDING_REVIEW', nullable=False),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_check_constraint(
        'ticket_drafts_status_check',
        'ticket_drafts',
        "status IN ('PENDING_REVIEW', 'POSTED', 'REJECTED')",
    )
    # The review queue is always read as "pending, for these agents".
    op.create_index('ix_ticket_drafts_org_status', 'ticket_drafts', ['org_id', 'status'])
    op.create_index('ix_ticket_drafts_agent_id', 'ticket_drafts', ['agent_id'])


def downgrade() -> None:
    op.drop_index('ix_ticket_drafts_agent_id', table_name='ticket_drafts')
    op.drop_index('ix_ticket_drafts_org_status', table_name='ticket_drafts')
    op.drop_constraint('ticket_drafts_status_check', 'ticket_drafts', type_='check')
    op.drop_table('ticket_drafts')
