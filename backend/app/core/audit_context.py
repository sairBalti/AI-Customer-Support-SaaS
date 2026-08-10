"""Request-scoped audit context (IP / User-Agent)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class AuditRequestContext:
    ip_address: str | None = None
    user_agent: str | None = None


_audit_request_context: ContextVar[AuditRequestContext | None] = ContextVar(
    "audit_request_context",
    default=None,
)


def set_audit_request_context(
    *,
    ip_address: str | None,
    user_agent: str | None,
) -> Token[AuditRequestContext | None]:
    return _audit_request_context.set(
        AuditRequestContext(ip_address=ip_address, user_agent=user_agent)
    )


def get_audit_request_context() -> AuditRequestContext:
    current = _audit_request_context.get()
    return current if current is not None else AuditRequestContext()


def clear_audit_request_context() -> None:
    _audit_request_context.set(None)
