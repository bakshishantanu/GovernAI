"""Legacy database vocabulary must not 500 a whole list response.

Both columns behind these fields are free text, not database enums, so a row
keeps whatever wrote it. Two real rows in the shared dev database were written
by an older seed script with values the API schemas did not accept, and each
one took down an entire page rather than rendering as one odd row:

- `agent_passports.compliance_status = "COMPLIANT"` -> GET /agents/ 500
- `skills.trust_level = "verified"` (lower case) -> GET /skills/ 500

The writers now agree on one vocabulary. These tests pin the tolerance that
keeps an older database working anyway.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.schemas.agent import PassportResponse
from app.api.schemas.skill import SkillResponse


def _passport(compliance_status: str) -> PassportResponse:
    now = datetime.now(timezone.utc)
    return PassportResponse.model_validate(
        {
            "id": uuid4(),
            "agent_id": uuid4(),
            "compliance_status": compliance_status,
            "lifecycle_state": "ACTIVE",
            "permissions": [],
            "created_at": now,
            "updated_at": now,
        }
    )


def _skill(trust_level: str) -> SkillResponse:
    return SkillResponse.model_validate(
        {
            "id": "ticketing",
            "name": "ticketing",
            "display_name": "Ticketing & ITSM",
            "description": "Create and resolve tickets",
            "version": "1.0",
            "trust_level": trust_level,
            "tools": [],
            "required_permissions": [],
        }
    )


def test_legacy_compliant_status_reads_as_passed():
    """The exact row that 500'd GET /agents/ against the shared database."""
    assert _passport("COMPLIANT").compliance_status == "PASSED"


@pytest.mark.parametrize("value", ["passed", "Passed", "  PASSED  "])
def test_compliance_status_is_case_and_space_insensitive(value):
    assert _passport(value).compliance_status == "PASSED"


def test_an_unknown_compliance_status_is_still_rejected():
    """Tolerance is for known older spellings, not for anything at all -- a
    value nothing ever wrote is a bug worth surfacing, not normalising away."""
    with pytest.raises(ValidationError):
        _passport("DEFINITELY_NOT_A_STATUS")


@pytest.mark.parametrize("value", ["verified", "Verified", "VERIFIED"])
def test_trust_level_is_case_insensitive(value):
    """The exact row that 500'd GET /skills/ against the shared database."""
    assert _skill(value).trust_level == "VERIFIED"


def test_an_unknown_trust_level_is_still_rejected():
    with pytest.raises(ValidationError):
        _skill("probably_fine")
