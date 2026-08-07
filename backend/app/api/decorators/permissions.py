"""Permission decorator helpers for FastAPI routes."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def permissions(*required: str) -> Callable[[F], F]:
    """Mark an endpoint with required permission names for RBAC middleware.

    Prefer dependency injection for authorization::

        @router.get("/x", dependencies=[Depends(require_permissions("x.read"))])

    This decorator additionally sets ``endpoint.permissions`` so
    ``RBACMiddleware`` can enforce the same list when the route object exposes
    it (FastAPI copies the attribute onto ``APIRoute`` when present).
    """

    def decorator(func: F) -> F:
        cast(Any, func).permissions = required
        return func

    return decorator
