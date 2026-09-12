from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class TrustLevel(str, Enum):
    VERIFIED = "VERIFIED"
    COMMUNITY = "COMMUNITY"
    EXPERIMENTAL = "EXPERIMENTAL"


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

    @abstractmethod
    def get_tools(self) -> list[BaseTool]: ...
