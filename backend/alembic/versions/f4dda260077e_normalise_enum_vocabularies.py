"""normalise_enum_vocabularies

Revision ID: f4dda260077e
Revises: 7a6f7b844de2
Create Date: 2026-09-10

Repairs every column in the database whose stored vocabulary disagrees with
what the API declares. Two of them make the API 500 outright; the third is
masked by a translation layer but stored wrong all the same.

Found by pointing the console at this database and walking every endpoint
(`GET /agents/` and `GET /skills/` returned 500), then sweeping all eleven
`Literal`-typed columns against their real values rather than assuming the
two failures were the whole story. The other eight columns are clean:
`agents.status`, `lifecycle_state`, `actor_type`, `policy_decision`,
`profiles.role`, `executions.status`, `rule_type`, `ticket_drafts.status`.

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

3. `cost_events.event_type = 'llm_inference'` (1 row) — the API declares
   `Literal["LLM_CALL", "TOOL_CALL"]`. This one never 500'd, because
   `api/v1/costs.py` translates it on the way out through `_EVENT_TYPE_ALIASES`.
   That workaround is deliberately left in place — it was a considered choice
   and removing it is a separate decision — but the *stored* value was wrong
   regardless, and that alias table falls back to "TOOL_CALL" for anything it
   does not recognise, so a bad value silently mislabels a cost event instead of
   surfacing. Normalising the data means the workaround stops being load-bearing
   even while it stays.

All three are normalised rather than the enums widened: 'COMPLIANT', 'verified'
and 'llm_inference' are not alternative spellings the API should learn to
accept, they are values nothing in either codebase ever intended to write. The
live writers were checked and are already correct — `agents/service.py` writes
PENDING/PASSED/FAILED, `TrustLevel.VERIFIED == "VERIFIED"`, and
`costs/service.py` writes "LLM_CALL" — so in every case the only source was
`scripts/seed_demo_data.py`, fixed alongside this migration.

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

    # Mirrors api/v1/costs.py's _EVENT_TYPE_ALIASES exactly, so the stored value
    # becomes whatever that translation layer was already showing. upper() alone
    # would not do: 'llm_inference' uppercases to 'LLM_INFERENCE', which is still
    # not a value the API accepts.
    op.execute(
        "UPDATE cost_events SET event_type = 'LLM_CALL' "
        "WHERE lower(event_type) IN ('llm_inference', 'llm_call')"
    )
    op.execute(
        "UPDATE cost_events SET event_type = 'TOOL_CALL' "
        "WHERE lower(event_type) = 'tool_call'"
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
    op.create_check_constraint(
        'cost_events_event_type_check',
        'cost_events',
        "event_type IN ('LLM_CALL', 'TOOL_CALL')",
    )


def downgrade() -> None:
    """Drops the guards only.

    The normalised values are deliberately left as they are: they are what the
    API has always required, and restoring 'COMPLIANT'/'verified'/'llm_inference'
    would only re-break the endpoints this migration exists to fix. Which rows
    originally held which spelling is not recorded, and is not worth recording.
    """
    op.drop_constraint('cost_events_event_type_check', 'cost_events', type_='check')
    op.drop_constraint('skills_trust_level_check', 'skills', type_='check')
    op.drop_constraint(
        'agent_passports_compliance_status_check', 'agent_passports', type_='check'
    )
