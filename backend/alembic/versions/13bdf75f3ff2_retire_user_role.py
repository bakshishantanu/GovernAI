"""retire_user_role

Revision ID: 13bdf75f3ff2
Revises: 7a1b2c3d4e5f
Create Date: 2026-09-10

Finishes the naming decision both sides landed on: "agent_builder" is the
permanent name, not "user" -- it's the one with real accounts already on it
(3 real rows on this database's team as of the last check, effectively none
on "user"), so there's real data to lose going the other direction and
essentially none going this one.

7a1b2c3d4e5f (PR #42) made both names valid aliases on purpose, as a safe
transition step. This migration is the second, final step: collapse to one
name for good. Idempotent -- safe to run even if there are no "user" rows
left; the backfill is a no-op in that case and the constraint narrowing
still needs to happen either way.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '13bdf75f3ff2'
down_revision: Union[str, Sequence[str], None] = '7a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
