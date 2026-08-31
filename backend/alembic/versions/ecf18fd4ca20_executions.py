"""executions

Revision ID: ecf18fd4ca20
Revises: c190a7e1346d
Create Date: 2026-08-31 13:24:35.505975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecf18fd4ca20'
down_revision: Union[str, Sequence[str], None] = 'c190a7e1346d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'executions',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('goal', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('result', sa.String(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_table(
        'execution_steps',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('execution_id', sa.UUID(), sa.ForeignKey('executions.id'), nullable=False),
        sa.Column('step_number', sa.Integer(), nullable=False),
        sa.Column('tool', sa.String(), nullable=True),
        sa.Column('tool_args', sa.JSON(), nullable=True),
        sa.Column('tool_result', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.execute('ALTER TABLE executions ENABLE ROW LEVEL SECURITY')
    op.execute('ALTER TABLE execution_steps ENABLE ROW LEVEL SECURITY')



def downgrade() -> None:
    pass # Implement as needed
