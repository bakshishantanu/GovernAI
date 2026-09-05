"""automations

Revision ID: a7c31f9d0b52
Revises: 1321726bf4c7
Create Date: 2026-09-05

Recipe-style rules, plus the record of every time one was evaluated.

`automation_runs.automation_id` is deliberately NOT ON DELETE CASCADE. Those
rows explain why an agent was suspended, and cascading would let deleting a
rule erase its own explanation. The API refuses to delete an automation that
has runs and tells the caller to disable it instead.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c31f9d0b52'
down_revision: Union[str, Sequence[str], None] = '1321726bf4c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'automations',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False, server_default=''),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        # Null means "every agent in the org".
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('trigger_type', sa.String(), nullable=False),
        sa.Column('trigger_config', sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column('action_type', sa.String(), nullable=False),
        sa.Column('action_config', sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )
    op.execute('ALTER TABLE automations ENABLE ROW LEVEL SECURITY')

    op.create_table(
        'automation_runs',
        sa.Column('id', sa.UUID(), primary_key=True),
        sa.Column('automation_id', sa.UUID(), sa.ForeignKey('automations.id'), nullable=False),
        sa.Column('org_id', sa.UUID(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('agent_id', sa.UUID(), sa.ForeignKey('agents.id'), nullable=True),
        sa.Column('triggered_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('outcome', sa.String(), nullable=False),
        sa.Column('detail', sa.String(), nullable=False, server_default=''),
        sa.Column('context', sa.dialects.postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'{}'::jsonb")),
    )
    op.execute('ALTER TABLE automation_runs ENABLE ROW LEVEL SECURITY')

    # The engine reads enabled rules per org on every relevant event, and the
    # console reads the newest runs; both deserve an index.
    op.create_index('ix_automations_org_enabled', 'automations', ['org_id', 'enabled'])
    op.create_index(
        'ix_automation_runs_org_time', 'automation_runs', ['org_id', 'triggered_at']
    )
    # The cooldown check counts a rule's recent FIRED runs for one agent.
    op.create_index(
        'ix_automation_runs_rule_agent',
        'automation_runs',
        ['automation_id', 'agent_id', 'triggered_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_automation_runs_rule_agent', table_name='automation_runs')
    op.drop_index('ix_automation_runs_org_time', table_name='automation_runs')
    op.drop_index('ix_automations_org_enabled', table_name='automations')
    op.drop_table('automation_runs')
    op.drop_table('automations')
