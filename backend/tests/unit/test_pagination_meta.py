"""Guards what a paginated `meta` block is actually allowed to carry.

`PaginatedMeta` is a strict pydantic model, so any key a route puts in its
`meta` dict that the model does not declare is silently discarded at
serialization time — no error, no warning, just a field the client never
receives. `/agents/` had been sending `total` since it was written, and it had
been dropped every single time.

These tests pin both halves of that: the declared fields survive, and the
undeclared ones are still dropped (so a future route cannot quietly invent a
meta key and assume it arrives).
"""

from app.api.schemas.common import PaginatedMeta, PaginatedResponse


def test_total_survives_serialization():
    """The regression itself: `total` must reach the client."""
    meta = PaginatedMeta.model_validate({"has_more": True, "total": 12})
    assert meta.total == 12
    assert meta.model_dump()["total"] == 12


def test_total_is_optional_for_routes_that_cannot_count():
    """`/costs/` deduces has_more from one extra row and has no count query."""
    meta = PaginatedMeta.model_validate({"has_more": False})
    assert meta.total is None


def test_undeclared_meta_keys_are_still_dropped():
    """The trap that caused this, kept visible rather than fixed by accident."""
    meta = PaginatedMeta.model_validate({"has_more": False, "limit": 50, "offset": 0})
    assert not hasattr(meta, "limit")
    assert "limit" not in meta.model_dump()


def test_agents_style_meta_round_trips_through_the_response_model():
    """The real path: a route hands `meta` a plain dict, not a PaginatedMeta."""
    response = PaginatedResponse[int](data=[1, 2, 3], meta={"has_more": True, "total": 12})
    dumped = response.model_dump()
    assert dumped["meta"]["total"] == 12
    assert dumped["meta"]["has_more"] is True
