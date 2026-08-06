"""HTTP authentication middleware."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.security.jwt import decode_access_token
from app.domain.exceptions.auth import TokenExpiredError, TokenInvalidError


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Parse optional Bearer tokens into ``request.state.token_claims``.

    Does not reject unauthenticated requests — endpoints enforce auth via
    ``CurrentActorDep`` / ``require_permissions``. Invalid tokens on protected
    routes are rejected by dependencies.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.token_claims = None
        request.state.auth_error = None
        authorization = request.headers.get("Authorization")
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            try:
                request.state.token_claims = decode_access_token(token)
            except (TokenInvalidError, TokenExpiredError) as exc:
                request.state.auth_error = exc
        return await call_next(request)
