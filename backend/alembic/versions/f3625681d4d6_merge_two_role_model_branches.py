"""merge_two_role_model_branches

Revision ID: f3625681d4d6
Revises: 75caa5b1d5f6, 7a1b2c3d4e5f
Create Date: 2026-09-10

DRAFT — cannot run yet. Written for review, not applied to any database.

Two independent "collapse to two roles" migration chains exist:

  ours:        ... -> 7a6f7b844de2 -> 75caa5b1d5f6 (two_role_model)
  Shantanu's:  ... -> 5372b78f87ee -> 7a1b2c3d4e5f (allow_user_and_agent_builder_roles,
               PR #42, feat/unified-auth-jwks, open/not merged at write time)

Neither branch's migration files exist in the other repo. This file references
'7a1b2c3d4e5f' and its own ancestor '5372b78f87ee' (PR #38/#42) before either has
landed here — alembic cannot resolve this revision graph until PR #42 (and the
PR #38 chain it sits on) is actually merged into this branch. Keep this file, but
do not expect `alembic history`/`alembic upgrade head` to work until then.

UPDATE (D-057): the two branches no longer disagree on the final answer, only on
how permanently to get there —

  - Ours (75caa5b1d5f6) now backfills every 'user' row to 'agent_builder' and
    NARROWS the constraint to ('admin', 'agent_builder') only — 'agent_builder'
    chosen because it's the name with real accounts already on it (confirmed
    live: 3 real rows across both known databases vs. essentially none on
    'user'), and the one already merged on `main`.
  - Shantanu's (7a1b2c3d4e5f) WIDENS the constraint to ('admin', 'agent_builder',
    'user') and never touches data, aliasing both names in the app layer
    (`CurrentUser.is_builder`) instead of collapsing one into the other.

A migration chain always runs every ancestor's own upgrade() on the way to a
merge point, so both of the above still happen regardless of what this file
does: '75caa5b1d5f6' narrows and backfills toward 'agent_builder'; separately,
Shantanu's branch may still have real 'user' rows reach this point (his side
never renames anything). **This migration's job is to make the end state
authoritative rather than order-dependent**: it re-backfills any 'user' rows
still present (catching whatever PR #42's branch let through) and re-asserts
the narrow, final constraint — 'user' is retired, not kept as a permanent
alias. Idempotent either way: if '75caa5b1d5f6' already did the backfill and
the narrowing, this is a no-op.

**Still needs Shantanu's agreement before this is safe to run for real** — D-057
is our own conclusion (his real accounts are the ones actually renamed under
this plan, from 'agent_builder' to itself, i.e. untouched; the only rows this
ever writes are stray 'user' rows, of which there are almost none known on
either side). Recorded here, not applied anywhere, not decided unilaterally.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3625681d4d6'
down_revision: Union[str, Sequence[str], None] = ('75caa5b1d5f6', '7a1b2c3d4e5f')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make the merge point authoritative: retire 'user' for good.

    Catches any 'user' rows that reached this point via the branch that
    never backfills (Shantanu's), then re-asserts the narrow constraint
    regardless of which parent's check constraint is currently in place.
    """
    op.execute("UPDATE profiles SET role = 'agent_builder' WHERE role = 'user'")

    op.execute("ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_role_check")
    op.create_check_constraint(
        'profiles_role_check', 'profiles', "role IN ('admin', 'agent_builder')"
    )


def downgrade() -> None:
    """No single correct narrower constraint to return to — both parent
    branches disagree on what state to restore. Left as a hard stop rather
    than guessing."""
    raise NotImplementedError(
        "This merge migration has no safe downgrade: 75caa5b1d5f6 and "
        "7a1b2c3d4e5f each expect a different prior constraint, and which "
        "rows were originally 'user' before this migration's backfill is not "
        "recoverable. Decide the right prior state by hand before downgrading "
        "past this point."
    )
