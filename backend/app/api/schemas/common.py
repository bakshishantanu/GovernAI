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

class PaginatedResponse(Envelope[list[T]], Generic[T]):
    meta: PaginatedMeta

class ErrorResponse(Envelope[None]):
    errors: list[ErrorDetail]

class HealthResponse(BaseModel):
    status: str
    version: str
