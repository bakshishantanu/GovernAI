"""Role-based access control for API routes.

FRD-01 defines two roles and what each may do:

- ``admin``  — full CRUD on agents, skills and policies; kill switch; all audit logs.
- ``member`` — create and view their own agents and their own audit logs.

``CurrentUser`` has carried a ``role`` since auth was built, but until now no route
read it, so a member could perform every admin action. These dependencies are the
enforcement point.
"""

from __future__ import annotations

from typing import Iterable

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


#: Admit administrators only. Use on anything that changes governance itself —
#: activating an agent, editing policy, or stopping a run.
require_admin = require_role("admin")
