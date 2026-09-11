"""The deterministic compliance check — FRD-03's four rules, as plain code.

Deliberately a pure function over plain data: no session, no repository, no
network. That is what makes FRD-03's "deterministic, not an LLM call" checkable
rather than merely asserted — you can read this one file and know exactly what
will be allowed. Everything needing the database is resolved by the caller and
passed in.

Returns a list of violations rather than a boolean because FRD-02 requires the
violations be shown to the user: an agent told only "no" cannot be fixed by the
person who built it.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Violation:
    """One broken rule. `rule` is stable and machine-readable; `message` is for a human."""

    rule: str
    message: str


def check_compliance(
    *,
    owner_id: UUID | None,
    owner_is_known: bool = True,
    skill_ids: Sequence[str],
    granted_permissions: Sequence[str],
    allowed_permissions: Sequence[str],
    forbidden_pairs: Sequence[tuple[str, str, str]],
) -> list[Violation]:
    """Evaluate all four rules and return every violation found.

    Every rule runs even when an earlier one has already failed: showing one
    problem, then another on the next attempt, wastes the builder's time.

    - `owner_is_known` — whether that owner is a real profile in the agent's own
      organisation. Resolved by the caller, because a pure function cannot look
      it up. Without it rule 1 is unfalsifiable through the API: `owner_id` is
      NOT NULL and taken from the caller's own token, so it can never be absent
      — but it can point at a profile that was deleted or belongs elsewhere.
    - `granted_permissions` — what the agent's passport actually holds.
    - `allowed_permissions` — the union of its bound skills' declared
      permissions, i.e. the ceiling it may not exceed.
    - `forbidden_pairs` — `(a, b, reason)` triples; order within a pair is
      irrelevant, so a rule need not be written twice.
    """
    violations: list[Violation] = []

    if owner_id is None:
        violations.append(Violation(rule="owner", message="Agent must have an owner."))
    elif not owner_is_known:
        violations.append(
            Violation(
                rule="owner",
                message="Agent's owner is not a member of this organisation.",
            )
        )

    if not skill_ids:
        violations.append(Violation(rule="skills", message="Agent must have at least one skill."))

    over = sorted(set(granted_permissions) - set(allowed_permissions))
    if over:
        violations.append(
            Violation(
                rule="permission_subset",
                message=(
                    "Permissions must come from the agent's skills. "
                    f"Not derivable from any bound skill: {', '.join(over)}."
                ),
            )
        )

    held = set(granted_permissions)
    for perm_a, perm_b, reason in forbidden_pairs:
        if perm_a in held and perm_b in held:
            violations.append(
                Violation(
                    rule="forbidden_pair",
                    message=(
                        f"Forbidden permission combination: '{perm_a}' with '{perm_b}' — {reason}."
                    ),
                )
            )

    return violations
