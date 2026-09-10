"""Unit tests for the /events/stream scoping rule (`is_event_visible`).

Pure-function tests, no DB/bus/HTTP — the route itself is a thin wrapper
around this that just resolves `allowed_agent_ids` from the database.

Two roles only (agent_builder merged into user — D-052): `allowed_agent_ids`
itself already carries the owner-OR-assigned union (resolved by
`refresh_scope()` in events.py using the repository's `visible_to_user_id`
filter), so this pure function only ever needs to check membership for a
non-admin "user" — there is no separate "builder" case left to test here.
"""

from app.api.v1.events import is_event_visible
from app.infrastructure.event_bus import Event

ORG = "00000000-0000-0000-0000-000000000000"
OTHER_ORG = "11111111-1111-1111-1111-111111111111"
USER = "22222222-2222-2222-2222-222222222222"
AGENT_MINE = "33333333-3333-3333-3333-333333333333"
AGENT_OTHER = "44444444-4444-4444-4444-444444444444"


def audit_event(agent_id: str, org_id: str = ORG) -> Event:
    return Event.create("audit.tool.denied", {"agent_id": agent_id, "org_id": org_id})


def request_event(requester_id: str, org_id: str = ORG) -> Event:
    return Event.create(
        "request_status", {"requester_id": requester_id, "org_id": org_id, "status": "PENDING"}
    )


def test_event_from_another_org_is_never_visible_to_anyone():
    event = audit_event(AGENT_MINE, org_id=OTHER_ORG)
    for role in ("admin", "user"):
        assert not is_event_visible(
            event, org_id=ORG, role=role, user_id=USER, allowed_agent_ids={AGENT_MINE}
        )


def test_admin_sees_every_agent_scoped_event_in_their_org_regardless_of_ownership():
    event = audit_event(AGENT_OTHER)
    assert is_event_visible(event, org_id=ORG, role="admin", user_id=USER, allowed_agent_ids=set())


def test_user_only_sees_agents_in_their_resolved_scope():
    """`allowed_agent_ids` already carries the owner-OR-assigned union
    resolved by refresh_scope() — this just confirms membership is honored
    either way, without re-deriving which column matched."""
    mine = audit_event(AGENT_MINE)
    others = audit_event(AGENT_OTHER)

    assert is_event_visible(
        mine, org_id=ORG, role="agent_builder", user_id=USER, allowed_agent_ids={AGENT_MINE}
    )
    assert not is_event_visible(
        others, org_id=ORG, role="agent_builder", user_id=USER, allowed_agent_ids={AGENT_MINE}
    )


def test_request_status_is_org_wide_for_admin():
    someone_elses_request = request_event(requester_id="99999999-9999-9999-9999-999999999999")

    assert is_event_visible(
        someone_elses_request, org_id=ORG, role="admin", user_id=USER, allowed_agent_ids=set()
    )


def test_request_status_is_private_to_its_requester_for_a_user():
    """Post-merge: a user builds only their own requests (see
    agent_requests.py's claim restriction), so the queue they watch live is
    their own too, not the org-wide queue agent_builder used to see."""
    mine = request_event(requester_id=USER)
    someone_elses = request_event(requester_id="99999999-9999-9999-9999-999999999999")

    assert is_event_visible(mine, org_id=ORG, role="agent_builder", user_id=USER, allowed_agent_ids=set())
    assert not is_event_visible(
        someone_elses, org_id=ORG, role="agent_builder", user_id=USER, allowed_agent_ids=set()
    )


def test_an_event_type_nobody_scoped_is_dropped_not_guessed():
    stray = Event.create("some.future.event", {"org_id": ORG, "agent_id": AGENT_MINE})
    assert not is_event_visible(
        stray, org_id=ORG, role="admin", user_id=USER, allowed_agent_ids=set()
    )
