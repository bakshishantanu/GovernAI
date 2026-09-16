from __future__ import annotations

from app.skills.base import BaseSkill, SkillRequirement, SkillRequirementField, TrustLevel


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
