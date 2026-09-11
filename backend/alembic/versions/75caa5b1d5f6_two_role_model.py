"""two_role_model

Revision ID: 75caa5b1d5f6
Revises: 7a6f7b844de2
Create Date: 2026-09-10 14:08:39.826455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75caa5b1d5f6'
down_revision: Union[str, Sequence[str], None] = '7a6f7b844de2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Two roles only, post mentor-meeting decision: 'user' and
    'agent_builder' collapse into one name. D-057: that name is
    'agent_builder', not 'user' -- it's the one with real accounts already on
    it (confirmed live, sixty-eighth/seventieth cycle DB inspection: 3 real
    'agent_builder' rows across both known databases vs. essentially none
    on 'user'), and it's already what's merged on `main` (PR #38/#42).
    Migrating the empty side costs nothing; migrating the populated side
    would mean renaming someone else's real accounts.

    Backfill first, then tighten the constraint -- doing it the other way
    round would reject the backfill's own UPDATE the instant it touched a
    still-'user' row."""
    op.execute("UPDATE profiles SET role = 'agent_builder' WHERE role = 'user'")

    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check', 'profiles', "role IN ('admin', 'agent_builder')"
    )


def downgrade() -> None:
    op.drop_constraint('profiles_role_check', 'profiles', type_='check')
    op.create_check_constraint(
        'profiles_role_check', 'profiles', "role IN ('admin', 'agent_builder', 'user')"
    )
    # Which 'agent_builder' rows were originally 'user' is not recoverable --
    # same limitation the three_role_model migration's own downgrade already
    # accepted for 'member' -> 'user'. Every non-admin row stays
    # 'agent_builder' on downgrade; re-promoting specific people back to
    # 'user', if this is ever actually rolled back, is a manual follow-up,
    # not this migration's job to guess at.
