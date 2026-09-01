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
    """JSON Schema for this tool's arguments, e.g. {"type": "object", "properties": {...}, "required": [...]}"""

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        ...

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
    def get_tools(self) -> list[BaseTool]:
        ...
