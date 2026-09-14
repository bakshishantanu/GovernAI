"""Ticket drafts escalate to UNDER_REVIEW instead of being rejected.

Rejecting a draft used to be a silent discard: the status flipped to
REJECTED and nothing happened on the ticket, leaving the person who raised
it with no idea anything had even been looked at. That status is replaced
with UNDER_REVIEW: escalating a draft now also posts a fixed, reassuring
reply back onto the ticket (same `add_reply` path Approve already uses), and
the ticket stays open/visible to reviewers rather than looking closed.

No existing rows use REJECTED (checked live: only PENDING_REVIEW and POSTED
exist), so this is a straight constraint swap, not a data migration.

Revision ID: e91a4c7d0f3b
Revises: d8e4f1a29b6c
Create Date: 2026-09-14
"""

from alembic import op

revision = "e91a4c7d0f3b"
down_revision = "d8e4f1a29b6c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ticket_drafts_status_check", "ticket_drafts", type_="check")
    op.create_check_constraint(
        "ticket_drafts_status_check",
        "ticket_drafts",
        "status IN ('PENDING_REVIEW', 'POSTED', 'UNDER_REVIEW')",
    )


def downgrade() -> None:
    op.drop_constraint("ticket_drafts_status_check", "ticket_drafts", type_="check")
    op.create_check_constraint(
        "ticket_drafts_status_check",
        "ticket_drafts",
        "status IN ('PENDING_REVIEW', 'POSTED', 'REJECTED')",
    )
