"""Regression test for a real, live-confirmed 500: DELETE /policies/{id}
crashed with a NOT NULL constraint violation whenever the policy had any
rules. Root cause: Policy.rules had no delete cascade, so SQLAlchemy's
default behaviour on deleting the parent is to try to null out the child's
policy_id foreign key rather than delete the child -- and policy_id is
NOT NULL. This can't be reproduced against a mock (it's a real DB
constraint), so it's verified by inspecting the mapper's own cascade
configuration directly, which is the actual thing that was wrong."""

from __future__ import annotations

import app.domain.agents.models  # noqa: F401 -- see test_compliance_events.py for why
import app.domain.permissions.models  # noqa: F401
from app.domain.policies.models import Policy
from sqlalchemy import inspect


def test_policy_rules_relationship_cascades_delete():
    mapper = inspect(Policy)
    rules_relationship = mapper.relationships["rules"]
    assert rules_relationship.cascade.delete is True
    assert rules_relationship.cascade.delete_orphan is True
