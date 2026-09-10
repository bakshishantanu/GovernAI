from app.skills.ticketing import (
    DraftTicketReplyTool,
    MockTicketingAdapter,
    ReadTicketTool,
    SearchTicketsTool,
    TicketDraftStore,
    TicketingSkill,
)


class FakeDraftStore(TicketDraftStore):
    """Captures what the tool tried to park for review."""

    def __init__(self) -> None:
        self.saved: list[tuple[str, str]] = []

    async def save_draft(self, ticket_id: str, body: str) -> str:
        self.saved.append((ticket_id, body))
        return "draft-1"


def test_skill_declares_correct_metadata_and_permissions():
    skill = TicketingSkill()

    assert skill.name == "ticketing"
    assert skill.required_permissions == ["ticket:read", "ticket:create"]

    tools = skill.get_tools()
    assert {t.name for t in tools} == {"read_ticket", "search_tickets", "draft_ticket_reply"}


async def test_read_ticket_found():
    adapter = MockTicketingAdapter()
    tool = ReadTicketTool(adapter)

    result = await tool.execute(ticket_id="TCK-1001")

    assert result["found"] is True
    assert result["subject"] == "Cannot reset password"


async def test_read_ticket_not_found():
    adapter = MockTicketingAdapter()
    tool = ReadTicketTool(adapter)

    result = await tool.execute(ticket_id="TCK-9999")

    assert result == {"found": False, "ticket_id": "TCK-9999"}


async def test_search_tickets_matches_subject_and_body():
    adapter = MockTicketingAdapter()
    tool = SearchTicketsTool(adapter)

    result = await tool.execute(query="password")

    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "TCK-1001"


async def test_search_tickets_no_match_returns_empty_list():
    adapter = MockTicketingAdapter()
    tool = SearchTicketsTool(adapter)

    result = await tool.execute(query="nonexistent-keyword-xyz")

    assert result["results"] == []


async def test_drafting_a_reply_saves_it_for_review():
    store = FakeDraftStore()
    tool = DraftTicketReplyTool(store)

    result = await tool.execute(ticket_id="TCK-1001", reply="Try clearing your browser cache.")

    assert result["success"] is True
    assert result["status"] == "PENDING_REVIEW"
    assert result["draft_id"] == "draft-1"
    assert store.saved == [("TCK-1001", "Try clearing your browser cache.")]


async def test_drafting_never_writes_to_the_ticket():
    """The whole point of the draft step: the agent cannot reach the ticket.

    A drafted reply must not show up on the ticket until a human approves it,
    so the ticketing backend has to be untouched after the tool runs.
    """
    adapter = MockTicketingAdapter()
    store = FakeDraftStore()
    skill = TicketingSkill(adapter=adapter, draft_store=store)

    draft_tool = next(t for t in skill.get_tools() if t.name == "draft_ticket_reply")
    await draft_tool.execute(ticket_id="TCK-1002", reply="Refund issued.")

    ticket = await adapter.get("TCK-1002")
    assert ticket.replies == []


async def test_drafting_without_a_store_reports_error_rather_than_raising():
    """A run must not die because drafting is unwired in this context."""
    tool = DraftTicketReplyTool(None)

    result = await tool.execute(ticket_id="TCK-1001", reply="hello")

    assert result["success"] is False
    assert result["error"] == "drafting_unavailable"
