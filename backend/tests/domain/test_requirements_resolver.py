from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain.connections.requirements import resolve_requirements


def _skill(
    skill_id: str, requirements: list[SimpleNamespace], permissions: list[str] | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        id=skill_id,
        requirements=requirements,
        permissions=[SimpleNamespace(permission=p) for p in (permissions or [])],
    )


def _document(status: str, access_scope: list[str] | None = None) -> SimpleNamespace:
    return SimpleNamespace(status=status, access_scope=access_scope or [])


def _requirement(key: str, type_: str, fields=None) -> SimpleNamespace:
    return SimpleNamespace(key=key, type=type_, label=key, description="", fields=fields or [])


@pytest.mark.asyncio
async def test_two_skills_sharing_a_requirement_key_dedupe_to_one_entry():
    org_id = uuid.uuid4()
    skill_repo = AsyncMock()
    skill_repo.get_skill.side_effect = lambda sid: {
        "doc_search": _skill("doc_search", [_requirement("documents", "file_upload")]),
        "other_doc_skill": _skill("other_doc_skill", [_requirement("documents", "file_upload")]),
    }[sid]
    connection_repo = AsyncMock()
    connection_repo.list_for_org.return_value = []
    document_repo = AsyncMock()
    document_repo.list_documents.return_value = []

    statuses = await resolve_requirements(
        org_id=org_id,
        skill_ids=["doc_search", "other_doc_skill"],
        skill_repo=skill_repo,
        connection_repo=connection_repo,
        document_repo=document_repo,
    )

    assert len(statuses) == 1
    assert statuses[0].key == "documents"


@pytest.mark.asyncio
async def test_file_upload_requirement_satisfied_by_a_ready_document_in_a_permitted_scope():
    org_id = uuid.uuid4()
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = _skill(
        "doc_search", [_requirement("documents", "file_upload")],
        permissions=["docs:search:public"],
    )
    connection_repo = AsyncMock()
    connection_repo.list_for_org.return_value = []
    document_repo = AsyncMock()
    document_repo.list_documents.return_value = [
        _document("PROCESSING", access_scope=["public"]),
        _document("READY", access_scope=["public"]),
    ]

    statuses = await resolve_requirements(
        org_id=org_id, skill_ids=["doc_search"],
        skill_repo=skill_repo, connection_repo=connection_repo, document_repo=document_repo,
    )

    assert statuses[0].satisfied is True


@pytest.mark.asyncio
async def test_file_upload_requirement_not_satisfied_by_a_document_outside_permitted_scope():
    """The skill can only search documents in the scopes its own permissions
    grant (docs:search:<scope>) -- a READY document in a scope it can't see
    must not report "Connected", or the Connections panel lies: the search
    tool would find nothing even though the badge says everything is set up."""
    org_id = uuid.uuid4()
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = _skill(
        "doc_search", [_requirement("documents", "file_upload")],
        permissions=["docs:search:public"],
    )
    connection_repo = AsyncMock()
    connection_repo.list_for_org.return_value = []
    document_repo = AsyncMock()
    document_repo.list_documents.return_value = [
        _document("READY", access_scope=["confidential"]),
    ]

    statuses = await resolve_requirements(
        org_id=org_id, skill_ids=["doc_search"],
        skill_repo=skill_repo, connection_repo=connection_repo, document_repo=document_repo,
    )

    assert statuses[0].satisfied is False


@pytest.mark.asyncio
async def test_credentials_requirement_satisfied_only_when_connection_exists():
    org_id = uuid.uuid4()
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = _skill(
        "ticketing", [_requirement("jira", "credentials")]
    )
    connection_repo = AsyncMock()
    connection_repo.list_for_org.return_value = []
    document_repo = AsyncMock()
    document_repo.list_documents.return_value = []

    unsatisfied = await resolve_requirements(
        org_id=org_id, skill_ids=["ticketing"],
        skill_repo=skill_repo, connection_repo=connection_repo, document_repo=document_repo,
    )
    assert unsatisfied[0].satisfied is False

    connection_repo.list_for_org.return_value = [SimpleNamespace(requirement_key="jira")]
    satisfied = await resolve_requirements(
        org_id=org_id, skill_ids=["ticketing"],
        skill_repo=skill_repo, connection_repo=connection_repo, document_repo=document_repo,
    )
    assert satisfied[0].satisfied is True


@pytest.mark.asyncio
async def test_unknown_skill_id_is_skipped_not_raised():
    skill_repo = AsyncMock()
    skill_repo.get_skill.return_value = None
    connection_repo = AsyncMock()
    connection_repo.list_for_org.return_value = []
    document_repo = AsyncMock()
    document_repo.list_documents.return_value = []

    statuses = await resolve_requirements(
        org_id=uuid.uuid4(), skill_ids=["deleted_skill"],
        skill_repo=skill_repo, connection_repo=connection_repo, document_repo=document_repo,
    )
    assert statuses == []
