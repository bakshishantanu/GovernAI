"""Agents can be deleted from any lifecycle state, but only soft-deleted.

An agent that has ever been ACTIVE can have real executions, cost events,
audit entries and ticket drafts pointing at it. Hard-deleting the row would
either cascade-destroy that history or orphan it, and the whole point of the
delete button is that the owner wants the agent gone *without* losing the
record of what it did. `deleted_at` lets the roster hide it while every log
table keeps its `agent_id` valid and every join keeps resolving its name.

Revision ID: d8e4f1a29b6c
Revises: c2f8a45d7e19
Create Date: 2026-09-13
"""

from alembic import op
import sqlalchemy as sa

revision = "d8e4f1a29b6c"
down_revision = "c2f8a45d7e19"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "deleted_at")
