from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, ClassVar


class TrustLevel(str, Enum):
    VERIFIED = "VERIFIED"
    COMMUNITY = "COMMUNITY"
    EXPERIMENTAL = "EXPERIMENTAL"


@dataclass(frozen=True)
class SkillRequirementField:
    """One input in a multi-field requirement, e.g. Jira's base URL / email /
    API token. `secret` marks a value that must never be echoed back to the
    frontend once saved (see ConnectionService.save_connection)."""

    key: str
    label: str
    secret: bool = False
    placeholder: str = ""


@dataclass(frozen=True)
class SkillRequirement:
    """Something an agent built with this skill needs before it can actually
    work — a connected account, uploaded documents, a webhook target. This is
    metadata only: it says what setup is needed, not how the frontend draws
    it (see the widget-type registry in agent-connections-panel.tsx) or how
    satisfaction is checked (see domain/connections/requirements.py).

    `type` is one of "credentials" (a small form, at least one field secret),
    "file_upload" (documents, checked against the existing documents table
    rather than the connections table), or "webhook" (a generated URL, no
    user input needed — satisfaction is always true once declared, since
    there is nothing to fill in; reserved for a later skill).
    """

    key: str
    type: str
    label: str
    description: str = ""
    fields: tuple[SkillRequirementField, ...] = ()


class BaseTool(ABC):
    """A single callable function within a skill, e.g. read_ticket(ticket_id)."""

    name: str
    description: str
    parameters: dict
    required_permission: str = ""
    """JSON Schema for this tool's arguments.

    e.g. {"type": "object", "properties": {...}, "required": [...]}
    """

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any: ...

    def enrich_arguments(self, arguments: dict, prior_messages: list[dict]) -> dict:
        """Hook to auto-fill arguments the model omitted, using the results of
        earlier tool calls in this same execution (see agent_graph.tools_node).

        Returns the arguments unchanged by default. A tool overrides this only
        when one of its optional arguments can be derived deterministically
        from prior tool output instead of depending on the model choosing to
        pass it (e.g. citing the document a preceding search actually found).
        """
        return arguments

    def audit_metadata(self, arguments: dict, result: Any) -> dict | None:
        """What of this call is worth keeping on the audit record.

        Returns None by default, which is the safe answer: a tool result can
        be large, and can contain content nobody decided should be copied into
        a second table. Only a tool that knows its own output is worth
        recording, and knows how to bound it, should override this.

        The case this exists for is retrieval. "search_documents was ALLOWED"
        tells a reader nothing about whether the answer was grounded; which
        chunks came back, from which document and page, and how relevant they
        scored, is the evidence. Without it the console cannot show what the
        model actually read, because nothing else on the run persists it (see
        governance/middleware.py, which drops the result after handing it to
        the model).
        """
        return None

    def to_openai_tool(self) -> dict:
        """Convert to the OpenAI/Groq function-calling tool format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class BaseSkill(ABC):
    """A reusable capability bundle: metadata + required permissions + its tools."""

    name: str
    display_name: str
    description: str
    version: str
    required_permissions: list[str]
    trust_level: TrustLevel
    requirements: ClassVar[list[SkillRequirement]] = []

    @abstractmethod
    def get_tools(self) -> list[BaseTool]: ...
