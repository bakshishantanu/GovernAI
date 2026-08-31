from dataclasses import asdict, dataclass, field

from app.skills.base import BaseSkill, BaseTool, TrustLevel


@dataclass
class Ticket:
    id: str
    subject: str
    body: str
    status: str
    requester: str
    replies: list[str] = field(default_factory=list)


class TicketingAdapter:
    """Mock, in-memory ticketing backend. A real adapter (Zendesk, Jira, ...)
    would implement these same three methods without the skill's tools
    needing to change at all.
    """

    def __init__(self, tickets: dict[str, Ticket] | None = None) -> None:
        self._tickets = tickets if tickets is not None else _seed_tickets()

    def get(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    def search(self, query: str) -> list[Ticket]:
        needle = query.lower()
        return [
            t
            for t in self._tickets.values()
            if needle in t.subject.lower() or needle in t.body.lower()
        ]

    def add_reply(self, ticket_id: str, reply: str) -> Ticket:
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            raise KeyError(ticket_id)
        ticket.replies.append(reply)
        return ticket


def _seed_tickets() -> dict[str, Ticket]:
    seed = [
        Ticket(
            id="TCK-1001",
            subject="Cannot reset password",
            body="I click 'forgot password' but never receive the reset email.",
            status="open",
            requester="alice@example.com",
        ),
        Ticket(
            id="TCK-1002",
            subject="Invoice #4521 shows wrong amount",
            body="The invoice total doesn't match what we agreed on in the contract.",
            status="open",
            requester="bob@example.com",
        ),
        Ticket(
            id="TCK-1003",
            subject="Feature request: dark mode",
            body="Would love a dark mode toggle in the settings page.",
            status="closed",
            requester="carol@example.com",
        ),
    ]
    return {t.id: t for t in seed}


class ReadTicketTool(BaseTool):
    name = "read_ticket"
    description = "Read a single ticket by its ID."
    required_permission = "ticket:read"
    parameters = {
        "type": "object",
        "properties": {"ticket_id": {"type": "string", "description": "e.g. TCK-1001"}},
        "required": ["ticket_id"],
    }

    def __init__(self, adapter: TicketingAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs) -> dict:
        ticket = self._adapter.get(kwargs["ticket_id"])
        if ticket is None:
            return {"found": False, "ticket_id": kwargs["ticket_id"]}
        return {"found": True, **asdict(ticket)}


class SearchTicketsTool(BaseTool):
    name = "search_tickets"
    description = "Search tickets by keyword appearing in the subject or body."
    required_permission = "ticket:read"
    parameters = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    }

    def __init__(self, adapter: TicketingAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs) -> dict:
        results = self._adapter.search(kwargs["query"])
        return {"results": [asdict(t) for t in results]}


class CreateTicketReplyTool(BaseTool):
    name = "create_ticket_reply"
    description = "Add a reply to an existing ticket."
    required_permission = "ticket:create"
    parameters = {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "reply": {"type": "string"},
        },
        "required": ["ticket_id", "reply"],
    }

    def __init__(self, adapter: TicketingAdapter) -> None:
        self._adapter = adapter

    async def execute(self, **kwargs) -> dict:
        try:
            ticket = self._adapter.add_reply(kwargs["ticket_id"], kwargs["reply"])
        except KeyError:
            return {"success": False, "error": "ticket_not_found", "ticket_id": kwargs["ticket_id"]}
        return {"success": True, "ticket_id": ticket.id, "reply_count": len(ticket.replies)}


class TicketingSkill(BaseSkill):
    name = "ticketing"
    display_name = "Ticketing"
    description = "Read, search, and reply to support tickets."
    version = "1.0.0"
    required_permissions = ["ticket:read", "ticket:create"]
    trust_level = TrustLevel.VERIFIED

    def __init__(self, adapter: TicketingAdapter | None = None) -> None:
        self._adapter = adapter or TicketingAdapter()

    def get_tools(self) -> list[BaseTool]:
        return [
            ReadTicketTool(self._adapter),
            SearchTicketsTool(self._adapter),
            CreateTicketReplyTool(self._adapter),
        ]
