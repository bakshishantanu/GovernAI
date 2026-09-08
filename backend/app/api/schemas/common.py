from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict | None = None
    errors: list[ErrorDetail] | None = None


class PaginatedMeta(BaseModel):
    next_cursor: str | None = None
    has_more: bool
    #: Total rows matching the query, ignoring limit/offset. Optional because
    #: not every list route can afford a second COUNT query — /costs/ deduces
    #: `has_more` from one extra row instead, and so reports no total. Routes
    #: that do count (e.g. /agents/) were already passing this and having it
    #: silently dropped: the field was never declared here, so pydantic
    #: discarded it and the console could not show "showing 5 of 12".
    total: int | None = None


class PaginatedResponse(Envelope[list[T]], Generic[T]):
    meta: PaginatedMeta


class ErrorResponse(Envelope[None]):
    errors: list[ErrorDetail]


class HealthResponse(BaseModel):
    status: str
    version: str
