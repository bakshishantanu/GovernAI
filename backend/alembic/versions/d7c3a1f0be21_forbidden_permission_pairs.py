"""forbidden_permission_pairs, and backfill agent permissions from skills

Revision ID: d7c3a1f0be21
Revises: acbf56ba6efa
Create Date: 2026-09-09

Two halves of the same fix (D-043).

1. `forbidden_permission_pairs` is FRD-03 rule 4 as *data*. No source document
   defines what a forbidden combination is — it is a project decision, and one
   that should be correctable without a redeploy. One pair is seeded, the one
   the demo's own narrative implies: an agent that can read payroll must not
   also be able to search the public document surface.

2. Every agent created through the console holds an *empty* permission set,
   because `create_agent` never derived permissions from its skills. The
   backfill grants each existing passport the union of its bound skills'
   permissions, skipping any it already holds.

Deliberately, the backfill does **not** re-check or demote anything already
ACTIVE. Granting an agent the permissions it was always meant to have is a
repair; silently suspending running agents from inside a migration is not.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7c3a1f0be21"
down_revision: Union[str, Sequence[str], None] = "acbf56ba6efa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SEEDED_PAIR = (
    "sql:read:internal_payroll",
    "docs:search:public",
    "an agent that can read payroll must not also search the public document surface",
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "forbidden_permission_pairs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("permission_a", sa.String(), nullable=False),
        sa.Column("permission_b", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.CheckConstraint("permission_a <> permission_b", name="forbidden_pair_distinct"),
    )

    # Order within a pair is not significant to the check, so the uniqueness has
    # to ignore it too — otherwise the same rule can be inserted twice, reversed,
    # and a builder is told about it twice.
    op.execute(
        "CREATE UNIQUE INDEX ix_forbidden_permission_pairs_unordered "
        "ON forbidden_permission_pairs ("
        "LEAST(permission_a, permission_b), GREATEST(permission_a, permission_b))"
    )

    op.execute(
        sa.text(
            "INSERT INTO forbidden_permission_pairs (permission_a, permission_b, reason) "
            "VALUES (:a, :b, :reason)"
        ).bindparams(a=_SEEDED_PAIR[0], b=_SEEDED_PAIR[1], reason=_SEEDED_PAIR[2])
    )

    # Backfill: every passport gets the union of its agent's skills' permissions,
    # minus whatever it already holds. NOT EXISTS rather than ON CONFLICT because
    # there is no unique constraint on (passport_id, permission) to conflict on.
    op.execute(
        """
        INSERT INTO permissions (id, passport_id, permission)
        SELECT gen_random_uuid(), p.id, sp.permission
        FROM agent_passports p
        JOIN agent_skills ags ON ags.agent_id = p.agent_id
        JOIN skill_permissions sp ON sp.skill_id = ags.skill_id
        WHERE NOT EXISTS (
            SELECT 1 FROM permissions existing
            WHERE existing.passport_id = p.id
              AND existing.permission = sp.permission
        )
        GROUP BY p.id, sp.permission
        """
    )


def downgrade() -> None:
    """Downgrade schema.

    The granted permissions are deliberately left in place: they are what the
    agents should always have held, and dropping them would re-break every
    passport rather than restore a previous state.
    """
    op.drop_index(
        "ix_forbidden_permission_pairs_unordered",
        table_name="forbidden_permission_pairs",
    )
    op.drop_table("forbidden_permission_pairs")
