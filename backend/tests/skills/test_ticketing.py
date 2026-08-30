from app.skills.ticketing import (
    CreateTicketReplyTool,
    ReadTicketTool,
    SearchTicketsTool,
    TicketingAdapter,
    TicketingSkill,
)


def test_skill_declares_correct_metadata_and_permissions():
    skill = TicketingSkill()

    assert skill.name == "ticketing"
    assert skill.required_permissions == ["ticket:read", "ticket:create"]

    tools = skill.get_tools()
    assert {t.name for t in tools} == {"read_ticket", "search_tickets", "create_ticket_reply"}


async def test_read_ticket_found():
    adapter = TicketingAdapter()
    tool = ReadTicketTool(adapter)

    result = await tool.execute(ticket_id="TCK-1001")

    assert result["found"] is True
    assert result["subject"] == "Cannot reset password"


async def test_read_ticket_not_found():
    adapter = TicketingAdapter()
    tool = ReadTicketTool(adapter)

    result = await tool.execute(ticket_id="TCK-9999")

    assert result == {"found": False, "ticket_id": "TCK-9999"}


async def test_search_tickets_matches_subject_and_body():
    adapter = TicketingAdapter()
    tool = SearchTicketsTool(adapter)

    result = await tool.execute(query="password")

    assert len(result["results"]) == 1
    assert result["results"][0]["id"] == "TCK-1001"


async def test_search_tickets_no_match_returns_empty_list():
    adapter = TicketingAdapter()
    tool = SearchTicketsTool(adapter)

    result = await tool.execute(query="nonexistent-keyword-xyz")

    assert result["results"] == []


async def test_create_ticket_reply_success():
    adapter = TicketingAdapter()
    tool = CreateTicketReplyTool(adapter)

    result = await tool.execute(ticket_id="TCK-1001", reply="Try clearing your browser cache.")

    assert result == {"success": True, "ticket_id": "TCK-1001", "reply_count": 1}
    assert adapter.get("TCK-1001").replies == ["Try clearing your browser cache."]


async def test_create_ticket_reply_on_missing_ticket_reports_error_not_exception():
    adapter = TicketingAdapter()
    tool = CreateTicketReplyTool(adapter)

    result = await tool.execute(ticket_id="TCK-9999", reply="hello")

    assert result == {"success": False, "error": "ticket_not_found", "ticket_id": "TCK-9999"}


async def test_shared_adapter_state_is_visible_across_tools():
    """The three tools must operate on the same underlying data when given the
    same adapter instance - a reply added via one tool is visible to another."""
    adapter = TicketingAdapter()
    skill = TicketingSkill(adapter=adapter)
    reply_tool, read_tool = None, None
    for tool in skill.get_tools():
        if tool.name == "create_ticket_reply":
            reply_tool = tool
        elif tool.name == "read_ticket":
            read_tool = tool

    await reply_tool.execute(ticket_id="TCK-1002", reply="Refund issued.")
    result = await read_tool.execute(ticket_id="TCK-1002")

    assert result["replies"] == ["Refund issued."]
