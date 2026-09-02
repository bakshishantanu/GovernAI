from unittest.mock import AsyncMock
from uuid import uuid4

from app.domain.skills.registry import SkillRegistry
from app.runtime.agent_loader import load_agent_tools


def _registry() -> SkillRegistry:
    return SkillRegistry(AsyncMock(), AsyncMock())


async def test_load_agent_tools_returns_tools_for_the_agents_bound_skills():
    agent_id = uuid4()
    agent_repo = AsyncMock()
    agent_repo.list_skill_ids.return_value = ["ticketing"]

    tools = await load_agent_tools(agent_id, agent_repo, _registry())

    agent_repo.list_skill_ids.assert_awaited_once_with(agent_id)
    assert {t.name for t in tools} == {"read_ticket", "search_tickets", "create_ticket_reply"}


async def test_load_agent_tools_returns_empty_list_for_an_agent_with_no_skills():
    agent_repo = AsyncMock()
    agent_repo.list_skill_ids.return_value = []

    tools = await load_agent_tools(uuid4(), agent_repo, _registry())

    assert tools == []
