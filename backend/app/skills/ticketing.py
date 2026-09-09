from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field

import httpx

from app.skills.base import BaseSkill, BaseTool, TrustLevel


@dataclass
class Ticket:
    id: str
    subject: str
    body: str
    status: str
    requester: str
    replies: list[str] = field(default_factory=list)


class TicketingAdapter(ABC):
    """A ticketing backend the skill's tools read from and write to. Real
    adapters (Jira, Zendesk, ...) implement these same three methods; the
    tools never know or care which one is underneath."""

    @abstractmethod
    async def get(self, ticket_id: str) -> Ticket | None: ...

    @abstractmethod
    async def search(self, query: str) -> list[Ticket]: ...

    @abstractmethod
    async def add_reply(self, ticket_id: str, reply: str) -> Ticket: ...


class MockTicketingAdapter(TicketingAdapter):
    """In-memory ticketing backend used when no real one is configured
    (local dev, tests, demos) -- see SkillRegistry."""

    def __init__(self, tickets: dict[str, Ticket] | None = None) -> None:
        self._tickets = tickets if tickets is not None else _seed_tickets()

    async def get(self, ticket_id: str) -> Ticket | None:
        return self._tickets.get(ticket_id)

    async def search(self, query: str) -> list[Ticket]:
        needle = query.lower()
        return [
            t
            for t in self._tickets.values()
            if needle in t.subject.lower() or needle in t.body.lower()
        ]

    async def add_reply(self, ticket_id: str, reply: str) -> Ticket:
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


def _adf_to_text(node: dict | None) -> str:
    """Flattens an Atlassian Document Format node tree (Jira's rich-text
    format for descriptions and comments) down to plain text. Only pulls
    out text content -- formatting, mentions, and other node types are
    dropped, which is all the LLM-facing tools need."""
    if not node:
        return ""
    parts: list[str] = []

    def walk(n: dict) -> None:
        if n.get("type") == "text":
            parts.append(n.get("text", ""))
        for child in n.get("content", []):
            walk(child)
        if n.get("type") == "paragraph":
            parts.append("\n")

    walk(node)
    return "".join(parts).strip()


def _text_to_adf(text: str) -> dict:
    """Wraps plain text back into the minimal ADF document Jira's comment
    API requires -- one paragraph node per blank-line-separated block."""
    paragraphs = text.split("\n\n") if text else [""]
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": p}]}
            for p in paragraphs
        ],
    }


def _ticket_from_issue(issue: dict) -> Ticket:
    fields = issue.get("fields", {})
    comments = (fields.get("comment") or {}).get("comments", [])
    reporter = fields.get("reporter") or {}
    return Ticket(
        id=issue["key"],
        subject=fields.get("summary", ""),
        body=_adf_to_text(fields.get("description")),
        status=(fields.get("status") or {}).get("name", ""),
        requester=reporter.get("emailAddress") or reporter.get("displayName", "unknown"),
        replies=[_adf_to_text(c.get("body")) for c in comments],
    )


_ISSUE_FIELDS = "summary,description,status,reporter,comment"


class JiraTicketingAdapter(TicketingAdapter):
    """Real Jira Cloud backend, via the REST API v3. Auth is HTTP Basic
    with an Atlassian account email + API token (Jira Cloud's supported
    method for this kind of server-to-server call)."""

    def __init__(self, base_url: str, email: str, api_token: str, project_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = (email, api_token)
        self._project_key = project_key

    async def get(self, ticket_id: str) -> Ticket | None:
        async with httpx.AsyncClient(auth=self._auth, timeout=10.0) as client:
            resp = await client.get(
                f"{self._base_url}/rest/api/3/issue/{ticket_id}",
                params={"fields": _ISSUE_FIELDS},
            )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return _ticket_from_issue(resp.json())

    async def search(self, query: str) -> list[Ticket]:
        # /rest/api/3/search (GET) is retired (HTTP 410) in favor of this
        # POST endpoint -- confirmed directly against a live site, not
        # assumed from docs. Response shape also changed: cursor-based
        # (nextPageToken/isLast), no more total/startAt.
        jql = f'project = {self._project_key} AND text ~ "{query}"'
        async with httpx.AsyncClient(auth=self._auth, timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/rest/api/3/search/jql",
                json={"jql": jql, "fields": _ISSUE_FIELDS.split(",")},
            )
        resp.raise_for_status()
        return [_ticket_from_issue(issue) for issue in resp.json().get("issues", [])]

    async def add_reply(self, ticket_id: str, reply: str) -> Ticket:
        async with httpx.AsyncClient(auth=self._auth, timeout=10.0) as client:
            resp = await client.post(
                f"{self._base_url}/rest/api/3/issue/{ticket_id}/comment",
                json={"body": _text_to_adf(reply)},
            )
            resp.raise_for_status()
        ticket = await self.get(ticket_id)
        if ticket is None:
            raise KeyError(ticket_id)
        return ticket


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
        ticket = await self._adapter.get(kwargs["ticket_id"])
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
        results = await self._adapter.search(kwargs["query"])
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
            ticket = await self._adapter.add_reply(kwargs["ticket_id"], kwargs["reply"])
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
        self._adapter = adapter or MockTicketingAdapter()

    def get_tools(self) -> list[BaseTool]:
        return [
            ReadTicketTool(self._adapter),
            SearchTicketsTool(self._adapter),
            CreateTicketReplyTool(self._adapter),
        ]
