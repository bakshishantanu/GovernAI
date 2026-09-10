"""normalise_enum_vocabularies

Revision ID: f4dda260077e
Revises: 7a6f7b844de2
Create Date: 2026-09-10

Repairs two rows-with-wrong-vocabulary in the database that make the API 500.
Found by pointing the console at this database and walking every endpoint:
`GET /agents/` and `GET /skills/` both returned 500, the rest were fine.

These are *data* faults, not schema drift between branches — `main` and the
console branch declare identical literals, so these rows break both backends
equally:

1. `agent_passports.compliance_status = 'COMPLIANT'` (1 row) — the API declares
   `Literal["PENDING", "PASSED", "FAILED"]`. One bad row fails response
   validation for the whole list, so `GET /agents/` 500s entirely and the
   console's Agents page renders as "No passports match", i.e. it looks like
   there are no agents rather than like something broke.

2. `skills.trust_level = 'verified'` (3 rows) — the API declares
   `Literal["VERIFIED", "COMMUNITY", "EXPERIMENTAL"]`. Same failure mode on
   `GET /skills/`. Purely a case mismatch.

Both are normalised rather than the enums widened: 'COMPLIANT' and 'verified'
are not alternative spellings the API should learn to accept, they are values
nothing in either codebase ever intended to write.

The CHECK constraints are the actual fix. Without them the same rows can be
written again tomorrow by any code path that bypasses the Pydantic layer
(a seed script, a manual dashboard edit), and the next person loses the same
hour working out why a page is mysteriously empty. Postgres refuses to add a
constraint that existing rows violate, so the backfills must run first.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f4dda260077e'
down_revision: Union[str, Sequence[str], None] = '7a6f7b844de2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 'COMPLIANT' meant a passport that had passed its compliance check.
    op.execute(
        "UPDATE agent_passports SET compliance_status = 'PASSED' "
        "WHERE compliance_status = 'COMPLIANT'"
    )
    # Defensive: same intent, other spellings, in case any exist.
    op.execute(
        "UPDATE agent_passports SET compliance_status = upper(compliance_status) "
        "WHERE compliance_status <> upper(compliance_status)"
    )
    op.execute(
        "UPDATE skills SET trust_level = upper(trust_level) "
        "WHERE trust_level <> upper(trust_level)"
    )

    op.create_check_constraint(
        'agent_passports_compliance_status_check',
        'agent_passports',
        "compliance_status IN ('PENDING', 'PASSED', 'FAILED')",
    )
    op.create_check_constraint(
        'skills_trust_level_check',
        'skills',
        "trust_level IN ('VERIFIED', 'COMMUNITY', 'EXPERIMENTAL')",
    )


def downgrade() -> None:
    """Drops the guards only.

    The normalised values are deliberately left as they are: they are what the
    API has always required, and restoring 'COMPLIANT'/'verified' would only
    re-break the two endpoints this migration exists to fix. Which rows
    originally held which spelling is not recorded, and is not worth recording.
    """
    op.drop_constraint('skills_trust_level_check', 'skills', type_='check')
    op.drop_constraint(
        'agent_passports_compliance_status_check', 'agent_passports', type_='check'
    )
