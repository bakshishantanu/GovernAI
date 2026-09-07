"""add budget_usd to agent_passports and fix event_type vocabulary

Revision ID: f1a2b3c4d5e6
Revises: 1321726bf4c7
Create Date: 2026-09-07 14:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str = "1321726bf4c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Feature #7: per-agent budget cap (nullable = falls back to env default)
    op.add_column("agent_passports", sa.Column("budget_usd", sa.Float(), nullable=True))

    # Bug #4: reconcile event_type vocabulary
    op.execute("UPDATE cost_events SET event_type = 'LLM_CALL' WHERE event_type = 'llm_inference'")
    op.execute("UPDATE cost_events SET event_type = 'TOOL_CALL' WHERE event_type = 'tool_call'")


def downgrade() -> None:
    op.execute("UPDATE cost_events SET event_type = 'llm_inference' WHERE event_type = 'LLM_CALL'")
    op.execute("UPDATE cost_events SET event_type = 'tool_call' WHERE event_type = 'TOOL_CALL'")
    op.drop_column("agent_passports", "budget_usd")
