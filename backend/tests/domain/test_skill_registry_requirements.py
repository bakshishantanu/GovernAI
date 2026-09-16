from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.domain.skills.models import SkillModel, SkillRequirementModel
from app.domain.skills.registry import SkillRegistry


def _fake_session():
    session = MagicMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_bootstrap_seeds_requirements_for_a_new_skill():
    skill_repo = MagicMock()
    skill_repo.get_skill = AsyncMock(return_value=None)
    session = _fake_session()

    registry = SkillRegistry(skill_repo=skill_repo, session=session)
    await registry.bootstrap()

    added_requirements = [
        call.args[0] for call in session.add.call_args_list
        if isinstance(call.args[0], SkillRequirementModel)
    ]
    jira_reqs = [r for r in added_requirements if r.key == "jira"]
    assert len(jira_reqs) == 1
    assert jira_reqs[0].type == "credentials"
    doc_reqs = [r for r in added_requirements if r.key == "documents"]
    assert len(doc_reqs) == 1


@pytest.mark.asyncio
async def test_bootstrap_resyncs_requirements_for_an_already_seeded_skill():
    """A second bootstrap() run (e.g. app restart after this code shipped, on
    a DB seeded before requirements existed) must not silently skip adding
    requirement rows just because the skill itself already exists."""
    existing_skill = SkillModel(
        id="ticketing", name="ticketing", display_name="Ticketing", description="d",
        version="1.0.0", trust_level="VERIFIED",
    )
    stale_requirement = SkillRequirementModel(
        id=uuid.uuid4(), skill_id="ticketing", key="stale", type="credentials", label="Stale",
    )
    existing_skill.requirements = [stale_requirement]

    skill_repo = MagicMock()
    skill_repo.get_skill = AsyncMock(
        side_effect=lambda skill_id: existing_skill if skill_id == "ticketing" else None
    )
    session = _fake_session()

    registry = SkillRegistry(skill_repo=skill_repo, session=session)
    await registry.bootstrap()

    session.delete.assert_any_call(stale_requirement)
    added_requirements = [
        call.args[0] for call in session.add.call_args_list
        if isinstance(call.args[0], SkillRequirementModel) and call.args[0].skill_id == "ticketing"
    ]
    assert any(r.key == "jira" for r in added_requirements)
    assert not any(r.key == "stale" for r in added_requirements)
