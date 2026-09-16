from __future__ import annotations

from uuid import UUID, uuid4

from app.domain.connections.crypto import encrypt_secret
from app.domain.connections.models import ConnectionModel
from app.domain.connections.repository import ConnectionRepository


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return f"****{value[-4:]}"


class ConnectionService:
    def __init__(self, repo: ConnectionRepository):
        self.repo = repo

    async def list_connections(self, org_id: UUID) -> list[ConnectionModel]:
        return await self.repo.list_for_org(org_id)

    async def save_connection(
        self,
        org_id: UUID,
        requirement_key: str,
        requirement_type: str,
        label: str,
        field_values: dict[str, str],
    ) -> ConnectionModel:
        """Every field is encrypted together (simplest correct thing -- this
        table holds nothing but connection secrets, so there is no per-field
        sensitivity distinction worth the complexity of encrypting some
        fields and not others). `preview` mirrors the same values back, with
        anything that doesn't read as a URL/email masked -- a base URL or
        email address shown in full makes "Connected as bot@acme.com" useful;
        masking it would add no real protection since those values were
        never secret."""
        secret_fields = {k: v for k, v in field_values.items() if v}
        preview = {
            k: v if ("://" in v or "@" in v) else _mask(v)
            for k, v in field_values.items()
        }

        connection = ConnectionModel(
            id=uuid4(),
            org_id=org_id,
            requirement_key=requirement_key,
            type=requirement_type,
            label=label,
            status="CONNECTED",
            encrypted_secret=encrypt_secret(secret_fields) if secret_fields else None,
            preview=preview,
        )
        return await self.repo.upsert(connection)

    async def delete_connection(self, org_id: UUID, requirement_key: str) -> bool:
        return await self.repo.delete(org_id, requirement_key)
