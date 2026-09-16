from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas.auth import CurrentUser
from app.api.schemas.common import Envelope
from app.api.schemas.connection import ConnectionResponse, SaveConnectionRequest
from app.domain.auth.middleware import get_current_user
from app.domain.auth.rbac import require_builder_or_admin
from app.domain.connections.repository import ConnectionRepository
from app.domain.connections.service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])


def get_connection_service(db: AsyncSession = Depends(get_db)) -> ConnectionService:
    return ConnectionService(repo=ConnectionRepository(db))


@router.get("/", response_model=Envelope[list[ConnectionResponse]])
async def list_connections(
    user: CurrentUser = Depends(get_current_user),
    service: ConnectionService = Depends(get_connection_service),
):
    """List this org's saved connections. Secrets are never included -- see
    ConnectionResponse.preview, which only ever carries masked values."""
    connections = await service.list_connections(user.org_id)
    return Envelope(data=connections)


@router.put("/{requirement_key}", response_model=Envelope[ConnectionResponse])
async def save_connection(
    requirement_key: str,
    payload: SaveConnectionRequest,
    user: CurrentUser = Depends(require_builder_or_admin),
    db: AsyncSession = Depends(get_db),
    service: ConnectionService = Depends(get_connection_service),
):
    """Create or update this org's connection for one skill requirement."""
    connection = await service.save_connection(
        org_id=user.org_id,
        requirement_key=requirement_key,
        requirement_type=payload.type,
        label=payload.label,
        field_values=payload.fields,
    )
    await db.commit()
    return Envelope(data=connection)


@router.delete("/{requirement_key}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(
    requirement_key: str,
    user: CurrentUser = Depends(require_builder_or_admin),
    db: AsyncSession = Depends(get_db),
    service: ConnectionService = Depends(get_connection_service),
):
    deleted = await service.delete_connection(user.org_id, requirement_key)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    await db.commit()
