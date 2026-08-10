"""Capture client IP / User-Agent for audit enrichment."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.audit_context import clear_audit_request_context, set_audit_request_context


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    if request.client is not None:
        return request.client.host
    return None


class AuditContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        set_audit_request_context(
            ip_address=_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )
        try:
            return await call_next(request)
        finally:
            clear_audit_request_context()
