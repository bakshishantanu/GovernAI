from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

class AgentRequestCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    requested_skills: list[str] = Field(default_factory=list)

class AgentRequestResponse(BaseModel):
    id: UUID
    org_id: UUID
    requester_id: UUID
    builder_id: UUID | None = None
    agent_id: UUID | None = None
    title: str
    description: str
    requested_skills: list[str]
    status: str
    created_at: datetime
    updated_at: datetime
    claimed_at: datetime | None = None
    fulfilled_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
