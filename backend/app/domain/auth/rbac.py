"""Role-based access control for API routes.

Two roles exist:

- ``admin``  — full CRUD on agents, skills and policies; kill switch; all audit
  and cost logs. Admin accounts are provisioned exclusively through a CLI command.
- ``agent_builder`` — create, build, request, claim, execute and monitor agents.
  This is the default role for all self-registering users.
"""

from __future__ import annotations

from collections.abc import Iterable

from fastapi import Depends, HTTPException, status

from app.api.schemas.auth import CurrentUser
from app.domain.auth.middleware import get_current_user


def require_role(*allowed: str):
    """Build a dependency that admits only the listed roles.

    Returns the ``CurrentUser`` unchanged when the role is allowed, so a route can
    swap ``Depends(get_current_user)`` for ``Depends(require_admin)`` without
    changing anything else in its signature.
    """

    allowed_roles: frozenset[str] = frozenset(allowed)

    async def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=_forbidden_message(allowed_roles),
            )
        return user

    return dependency


def _forbidden_message(allowed_roles: Iterable[str]) -> str:
    roles = " or ".join(sorted(allowed_roles))
    return f"This action requires the {roles} role"


#: Admit administrators only.
require_admin = require_role("admin")

#: Admit regular users.
require_user = require_role("agent_builder")

#: Admit either role — i.e. any authenticated caller. Kept as its own name
#: (rather than inlining `require_role("agent_builder", "admin")` at each call
#: site) because its call sites predate the two-role merge and read more
#: clearly keeping their original name: "build/submit/activate an agent",
#: "claim a request", "view costs" were agent_builder-or-admin actions from
#: the start, not actions that were ever meant to be admin-only.
require_builder_or_admin = require_role("agent_builder", "admin")
