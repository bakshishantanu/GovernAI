"""three_role_model

Revision ID: acbf56ba6efa
Revises: f1a2b3c4d5e6
Create Date: 2026-09-08 20:46:52.124791

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acbf56ba6efa'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create agent_requests table
    op.create_table(
        'agent_requests',
        sa.Column('id', sa.dialects.postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('org_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('requester_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('builder_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=True),
        sa.Column('agent_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requested_skills', sa.dialects.postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='PENDING', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('fulfilled_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('PENDING', 'CLAIMED', 'FULFILLED', 'CANCELLED')", name='agent_requests_status_check')
    )

    op.create_index('ix_agent_requests_org_status', 'agent_requests', ['org_id', 'status'])
    op.create_index('ix_agent_requests_requester', 'agent_requests', ['requester_id'])
    op.create_index('ix_agent_requests_builder', 'agent_requests', ['builder_id'])
    
    # Partial unique index (agent_id can be mapped to max 1 request)
    op.execute("CREATE UNIQUE INDEX ix_agent_requests_agent ON agent_requests(agent_id) WHERE agent_id IS NOT NULL")

    # 2. Add assigned_user_id and request_id to agents table
    op.add_column('agents', sa.Column('assigned_user_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('profiles.id'), nullable=True))
    op.add_column('agents', sa.Column('request_id', sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_requests.id'), nullable=True))
    op.execute("CREATE INDEX ix_agents_assigned_user ON agents(assigned_user_id) WHERE assigned_user_id IS NOT NULL")

    # 3. Add CHECK constraint on profiles.role and data migration for 'member' -> 'user'
    # Data migration
    op.execute("UPDATE profiles SET role = 'user' WHERE role = 'member'")
    
    # Add check constraint for valid roles
    op.create_check_constraint('profiles_role_check', 'profiles', "role IN ('admin', 'agent_builder', 'user')")


def downgrade() -> None:
    """Downgrade schema."""
    # Remove check constraint
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    
    # Data migration back to 'member' from 'user'
    op.execute("UPDATE profiles SET role = 'member' WHERE role = 'user'")

    # Remove columns from agents table
    op.execute("DROP INDEX IF EXISTS ix_agents_assigned_user")
    op.drop_column('agents', 'request_id')
    op.drop_column('agents', 'assigned_user_id')

    # Drop agent_requests table
    op.execute("DROP INDEX IF EXISTS ix_agent_requests_agent")
    op.drop_index('ix_agent_requests_builder', table_name='agent_requests')
    op.drop_index('ix_agent_requests_requester', table_name='agent_requests')
    op.drop_index('ix_agent_requests_org_status', table_name='agent_requests')
    op.drop_table('agent_requests')
