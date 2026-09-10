"""Email decides role, not anything client-supplied.

`app_metadata.role` on the Supabase JWT used to be the source of truth, but
that field is arbitrary claim data a project admin sets by hand in the
Supabase dashboard - nothing in this codebase enforced it stayed in sync with
who someone actually is. Deciding role from the authenticated email itself
closes that gap: whoever owns `admin@governai.com`'s inbox is the only person
who can ever sign in as admin, full stop.
"""

from __future__ import annotations

from app.config import settings

Role = str  # "admin" | "agent_builder" — see api/schemas/auth.py


def _parse_email_list(raw: str) -> frozenset[str]:
    return frozenset(email.strip().lower() for email in raw.split(",") if email.strip())


def resolve_role_by_email(email: str | None, *, admin_emails: str) -> Role:
    """Pure function: which role a given email gets, given the configured admin list.

    Two roles only (post mentor-meeting decision): an email on the admin list
    gets "admin"; everything else - including no email at all, which a
    misconfigured token could still produce - gets "agent_builder", the
    least-privileged role (D-057: standardized on this name over "user" since
    it's the one with real accounts on it — see DECISIONS.md). Never silently
    promotes.
    """
    if not email:
        return "agent_builder"

    normalized = email.strip().lower()
    if normalized in _parse_email_list(admin_emails):
        return "admin"
    return "agent_builder"


def role_for_email(email: str | None) -> Role:
    """Convenience wrapper reading the admin list from the running config."""
    return resolve_role_by_email(email, admin_emails=settings.ADMIN_EMAILS)
