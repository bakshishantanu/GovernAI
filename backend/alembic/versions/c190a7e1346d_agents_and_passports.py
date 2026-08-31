"""agents and passports

Revision ID: c190a7e1346d
Revises: b36db6e4a73e
Create Date: 2026-08-31 13:24:34.390281

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c190a7e1346d'
down_revision: Union[str, Sequence[str], None] = 'b36db6e4a73e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'agents',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('owner_id', sa.UUID(), sa.ForeignKey('profiles.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_table(
        'agent_passports',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('compliance_status', sa.String(), nullable=False),
        sa.Column('compliance_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('lifecycle_state', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.execute('ALTER TABLE agents ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE agent_passports ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
