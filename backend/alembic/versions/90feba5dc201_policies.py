"""policies

Revision ID: 90feba5dc201
Revises: b74a36cd0c25
Create Date: 2026-08-31 13:24:37.882073

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '90feba5dc201'
down_revision: Union[str, Sequence[str], None] = 'b74a36cd0c25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'policies',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_table(
        'policy_rules',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('policy_id', sa.UUID(), sa.ForeignKey('policies.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('rule_type', sa.String(), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.execute('ALTER TABLE policies ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE policy_rules ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
