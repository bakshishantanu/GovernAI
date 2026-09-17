from __future__ import annotations

import uuid

from app.api.schemas.skill import SkillRequirementResponse, SkillResponse
from app.domain.skills.models import SkillModel, SkillPermission, SkillRequirementModel
from app.skills.base import BaseSkill, SkillRequirement, SkillRequirementField, TrustLevel
from app.skills.document_search import DocumentSearchSkill
from app.skills.ticketing import TicketingSkill


def test_base_skill_has_no_requirements_by_default():
    class NoRequirementsSkill(BaseSkill):
        name = "no_reqs"
        display_name = "No Requirements"
        description = "d"
        version = "1.0.0"
        trust_level = TrustLevel.VERIFIED
        required_permissions = []

        def get_tools(self):
            return []

    assert NoRequirementsSkill().requirements == []


def test_skill_requirement_field_defaults():
    field = SkillRequirementField(key="api_token", label="API token", secret=True)
    assert field.placeholder == ""
    assert field.secret is True


def test_skill_requirement_carries_fields():
    req = SkillRequirement(
        key="jira",
        type="credentials",
        label="Jira account",
        description="Needed to read and post tickets.",
        fields=(SkillRequirementField(key="api_token", label="API token", secret=True),),
    )
    assert req.type == "credentials"
    assert len(req.fields) == 1
    assert req.fields[0].key == "api_token"


def test_ticketing_skill_requires_jira_credentials():
    reqs = TicketingSkill(adapter=None).requirements
    assert len(reqs) == 1
    assert reqs[0].key == "jira"
    assert reqs[0].type == "credentials"
    field_keys = {f.key for f in reqs[0].fields}
    assert field_keys == {"base_url", "email", "api_token"}
    secret_fields = {f.key for f in reqs[0].fields if f.secret}
    assert secret_fields == {"api_token"}


def test_document_search_skill_requires_file_upload():
    reqs = DocumentSearchSkill(permitted_scopes={"public"}).requirements
    assert len(reqs) == 1
    assert reqs[0].key == "documents"
    assert reqs[0].type == "file_upload"


def test_skill_response_serializes_requirements():
    db_skill = SkillModel(
        id="ticketing", name="ticketing", display_name="Ticketing", description="d",
        version="1.0.0", trust_level="VERIFIED",
    )
    db_skill.tools = []
    db_skill.permissions = []
    db_skill.requirements = [
        SkillRequirementModel(
            id=uuid.uuid4(), skill_id="ticketing", key="jira", type="credentials",
            label="Jira account", description="Needed to read and post tickets.",
            fields=[{"key": "api_token", "label": "API token", "secret": True, "placeholder": ""}],
        )
    ]

    response = SkillResponse.model_validate(db_skill)

    assert len(response.requirements) == 1
    assert response.requirements[0].key == "jira"
    assert response.requirements[0].fields[0].secret is True


def test_skill_requirement_response_normalizes_a_null_fields_column_to_empty_list():
    """Defense in depth: registry.bootstrap() is now the only writer and
    always writes a list (see the fix for the real /skills/ 500 this caused),
    but a stale/manually-inserted row could still have fields=None in the DB
    -- the schema should not blow up the whole endpoint over one bad row."""
    response = SkillRequirementResponse.model_validate(
        {"key": "documents", "type": "file_upload", "label": "Docs", "fields": None}
    )
    assert response.fields == []


def test_skill_response_required_permissions_reflects_real_skill_permissions():
    """SkillModel's ORM attribute is `permissions` (see domain/skills/models.py),
    not `required_permissions` -- a field named `required_permissions` with no
    validation_alias pointing at `permissions` reads nothing from a real ORM
    object under `from_attributes=True` and silently falls back to its `[]`
    default, no matter how many SkillPermission rows the skill actually has.
    This is what the create-agent modal shows the builder under 'permissions
    are derived, never hand-picked' -- if it's always empty, that promise is a
    lie. The actual grant (AgentService.create_agent) is unaffected, since it
    reads `skill.permissions` directly in Python rather than through this
    schema -- this bug is specifically about what gets *displayed*."""
    db_skill = SkillModel(
        id="ticketing", name="ticketing", display_name="Ticketing", description="d",
        version="1.0.0", trust_level="VERIFIED",
    )
    db_skill.tools = []
    db_skill.requirements = []
    db_skill.permissions = [
        SkillPermission(id=uuid.uuid4(), skill_id="ticketing", permission="ticket:read"),
        SkillPermission(id=uuid.uuid4(), skill_id="ticketing", permission="ticket:create"),
    ]

    response = SkillResponse.model_validate(db_skill)

    assert set(response.required_permissions) == {"ticket:read", "ticket:create"}
