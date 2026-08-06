"""RBAC permission helpers.

Prefer ``Depends(require_permissions(...))`` from ``app.api.deps`` in routers.
"""

from __future__ import annotations

from app.application.context import RequestActor
from app.domain.exceptions.auth import InsufficientPermissionError, TokenInvalidError


def ensure_permissions(actor: RequestActor, *permissions: str) -> RequestActor:
    """Imperative permission check for services/use-cases."""
    if actor.is_super_admin:
        return actor
    if actor.user_id is None:
        raise TokenInvalidError("Authentication required.")
    if not actor.has_all_permissions(*permissions):
        raise InsufficientPermissionError(
            f"Missing permission(s): {', '.join(permissions)}",
        )
    return actor
