import uuid
from app.api.v1.events import is_event_visible
from app.infrastructure.event_bus import Event


def test_is_event_visible_org_mismatch_dropped():
    org1 = str(uuid.uuid4())
    org2 = str(uuid.uuid4())
    event = Event.create("cost.llm.incurred", {"org_id": org1, "agent_id": "agent-1"})

    assert not is_event_visible(
        event,
        org_id=org2,
        role="admin",
        user_id="user-1",
        allowed_agent_ids={"agent-1"},
    )


def test_is_event_visible_admin_sees_all_in_org():
    org_id = str(uuid.uuid4())
    event = Event.create("audit.tool.allowed", {"org_id": org_id, "agent_id": "unrelated-agent"})

    assert is_event_visible(
        event,
        org_id=org_id,
        role="admin",
        user_id="user-1",
        allowed_agent_ids=set(),
    )


def test_is_event_visible_builder_sees_only_allowed_agents():
    org_id = str(uuid.uuid4())
    event1 = Event.create("cost.llm.incurred", {"org_id": org_id, "agent_id": "my-agent"})
    event2 = Event.create("cost.llm.incurred", {"org_id": org_id, "agent_id": "other-agent"})

    assert is_event_visible(
        event1,
        org_id=org_id,
        role="agent_builder",
        user_id="user-1",
        allowed_agent_ids={"my-agent"},
    )
    assert not is_event_visible(
        event2,
        org_id=org_id,
        role="agent_builder",
        user_id="user-1",
        allowed_agent_ids={"my-agent"},
    )


def test_is_event_visible_request_status_scoping():
    org_id = str(uuid.uuid4())
    my_user_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())

    my_request = Event.create(
        "request_status",
        {"org_id": org_id, "requester_id": my_user_id, "status": "APPROVED"},
    )
    other_request = Event.create(
        "request_status",
        {"org_id": org_id, "requester_id": other_user_id, "status": "APPROVED"},
    )

    # Builder only sees their own requests
    assert is_event_visible(
        my_request,
        org_id=org_id,
        role="agent_builder",
        user_id=my_user_id,
        allowed_agent_ids=set(),
    )
    assert not is_event_visible(
        other_request,
        org_id=org_id,
        role="agent_builder",
        user_id=my_user_id,
        allowed_agent_ids=set(),
    )

    # Admin sees all requests in org
    assert is_event_visible(
        other_request,
        org_id=org_id,
        role="admin",
        user_id=my_user_id,
        allowed_agent_ids=set(),
    )
