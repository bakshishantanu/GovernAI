from __future__ import annotations

import os
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    from app.api.schemas.auth import Role


def get_admin_emails() -> set[str]:
    """Return the set of lowercase email addresses configured as administrators."""
    raw = os.environ.get("ADMIN_EMAILS") or settings.ADMIN_EMAILS or ""
    if not raw:
        return set()
    return {email.strip().lower() for email in raw.split(",") if email.strip()}


def is_admin_email(email: str | None) -> bool:
    """Check whether the given email address is in the admin allowlist."""
    if not email:
        return False
    return email.strip().lower() in get_admin_emails()


def resolve_role(email: str | None, raw_role: str | None) -> Role:
    """Resolve user role based on email allowlist and token app_metadata.

    Priority:
    1. If user's email is in ADMIN_EMAILS -> 'admin'.
    2. If token app_metadata role is 'admin' -> 'admin'.
    3. If token app_metadata role is 'user' or 'agent_builder' -> preserve role.
    4. Default fallback -> 'agent_builder'.
    """
    if is_admin_email(email):
        return "admin"

    if raw_role == "admin":
        return "admin"

    if raw_role in ("user", "agent_builder"):
        return raw_role  # type: ignore[return-value]

    return "agent_builder"
