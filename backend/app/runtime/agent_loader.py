from __future__ import annotations
from uuid import UUID

from app.domain.agents.repository import AgentRepository
from app.domain.skills.registry import SkillRegistry
from app.skills.base import BaseTool


async def load_agent_tools(
    agent_id: UUID,
    agent_repo: AgentRepository,
    skill_registry: SkillRegistry,
) -> list[BaseTool]:
    """Resolves an agent's bound skills into the tool list to pass into
    build_agent_graph, so a run only ever sees the tools that agent owns."""
    skill_ids = await agent_repo.list_skill_ids(agent_id)
    return skill_registry.get_tools(skill_ids)
