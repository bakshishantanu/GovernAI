from __future__ import annotations
from typing import TypeVar, Generic, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')

class ErrorDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: Optional[str] = None

class Envelope(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: Optional[dict] = None
    errors: Optional[list[ErrorDetail]] = None

class PaginatedMeta(BaseModel):
    next_cursor: Optional[str] = None
    has_more: bool
    #: Total rows matching the query, ignoring limit/offset. Optional because
    #: not every list route can afford a second COUNT query — /costs/ deduces
    #: `has_more` from one extra row instead, and so reports no total. Routes
    #: that do count (e.g. /agents/) were already passing this and having it
    #: silently dropped: the field was never declared here, so pydantic
    #: discarded it and the console could not show "showing 5 of 12".
    total: Optional[int] = None

class PaginatedResponse(Envelope[list[T]], Generic[T]):
    meta: PaginatedMeta

class ErrorResponse(Envelope[None]):
    errors: list[ErrorDetail]

class HealthResponse(BaseModel):
    status: str
    version: str
