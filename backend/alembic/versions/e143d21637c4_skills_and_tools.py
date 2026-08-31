"""skills and tools

Revision ID: e143d21637c4
Revises: 90feba5dc201
Create Date: 2026-08-31 13:24:39.075736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e143d21637c4'
down_revision: Union[str, Sequence[str], None] = '90feba5dc201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.create_table(
        'skills',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('display_name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('trust_level', sa.String(), nullable=False)
    )
    op.create_table(
        'skill_permissions',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('skill_id', sa.String(), sa.ForeignKey('skills.id'), nullable=False),
        sa.Column('permission', sa.String(), nullable=False)
    )
    op.create_table(
        'tools',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('skill_id', sa.String(), sa.ForeignKey('skills.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('required_permission', sa.String(), nullable=False)
    )
    op.create_table(
        'agent_skills',
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), primary_key=True),
        sa.Column('skill_id', sa.String(), sa.ForeignKey('skills.id'), primary_key=True)
    )



def downgrade() -> None:
    pass # Implement as needed
