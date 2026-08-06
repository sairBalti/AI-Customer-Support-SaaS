"""RBAC middleware for routes that declare required permissions."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.responses.envelopes import error_envelope


class RBACMiddleware(BaseHTTPMiddleware):
    """Enforce permissions declared on ``request.scope['route'].permissions``.

    Attach permissions when including routers, e.g.::

        route.permissions = ("companies.manage",)

    Unauthenticated/unauthorized requests receive standardized envelopes.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        route = request.scope.get("route")
        required = getattr(route, "permissions", None) if route is not None else None
        if not required:
            return await call_next(request)

        actor = getattr(request.state, "actor", None)
        if actor is None or actor.user_id is None:
            return JSONResponse(
                status_code=401,
                content=error_envelope("INVALID_TOKEN", "Authentication required."),
            )
        if not actor.has_all_permissions(*required):
            return JSONResponse(
                status_code=403,
                content=error_envelope(
                    "INSUFFICIENT_PERMISSION",
                    f"Missing permission(s): {', '.join(required)}",
                ),
            )
        return await call_next(request)
