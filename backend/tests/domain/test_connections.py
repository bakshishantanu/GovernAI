from __future__ import annotations

import uuid

import pytest

from app.domain.connections.crypto import decrypt_secret, encrypt_secret
from app.domain.connections.models import ConnectionModel
from app.domain.connections.service import ConnectionService


def test_encrypt_decrypt_round_trip():
    token = encrypt_secret({"api_token": "sk-super-secret"})
    assert "sk-super-secret" not in token
    assert decrypt_secret(token) == {"api_token": "sk-super-secret"}


class _FakeConnectionRepository:
    def __init__(self):
        self.saved: list[ConnectionModel] = []

    async def list_for_org(self, org_id):
        return [c for c in self.saved if c.org_id == org_id]

    async def get(self, org_id, requirement_key):
        return next(
            (c for c in self.saved if c.org_id == org_id and c.requirement_key == requirement_key),
            None,
        )

    async def upsert(self, connection):
        existing = await self.get(connection.org_id, connection.requirement_key)
        if existing:
            self.saved.remove(existing)
        self.saved.append(connection)
        return connection

    async def delete(self, org_id, requirement_key):
        existing = await self.get(org_id, requirement_key)
        if not existing:
            return False
        self.saved.remove(existing)
        return True


@pytest.mark.asyncio
async def test_save_connection_masks_secret_in_preview_and_encrypts_it():
    org_id = uuid.uuid4()
    service = ConnectionService(repo=_FakeConnectionRepository())

    connection = await service.save_connection(
        org_id=org_id,
        requirement_key="jira",
        requirement_type="credentials",
        label="Jira account",
        field_values={
            "base_url": "https://acme.atlassian.net",
            "email": "bot@acme.com",
            "api_token": "sk-abcdef123456",
        },
    )

    assert connection.status == "CONNECTED"
    assert connection.encrypted_secret is not None
    assert "sk-abcdef123456" not in str(connection.preview)
    assert connection.preview["base_url"] == "https://acme.atlassian.net"
    assert connection.preview["api_token"].endswith("3456")
    assert connection.preview["api_token"].startswith("****")


@pytest.mark.asyncio
async def test_delete_connection_returns_false_when_nothing_to_delete():
    service = ConnectionService(repo=_FakeConnectionRepository())
    assert await service.delete_connection(uuid.uuid4(), "jira") is False


@pytest.mark.asyncio
async def test_list_connections_scoped_to_org():
    org_a, org_b = uuid.uuid4(), uuid.uuid4()
    service = ConnectionService(repo=_FakeConnectionRepository())
    await service.save_connection(
        org_id=org_a, requirement_key="jira", requirement_type="credentials",
        label="Jira", field_values={"api_token": "x"},
    )
    await service.save_connection(
        org_id=org_b, requirement_key="jira", requirement_type="credentials",
        label="Jira", field_values={"api_token": "y"},
    )

    only_a = await service.list_connections(org_a)
    assert len(only_a) == 1
    assert only_a[0].org_id == org_a
