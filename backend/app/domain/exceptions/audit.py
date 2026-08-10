"""Audit log domain exceptions."""

from app.domain.exceptions.base import DomainError


class AuditLogNotFoundError(DomainError):
    code = "AUDIT_LOG_NOT_FOUND"

    def __init__(self, message: str = "Audit log not found.") -> None:
        super().__init__(message)


class AuditLogAccessDeniedError(DomainError):
    code = "AUDIT_LOG_ACCESS_DENIED"

    def __init__(self, message: str = "Access to audit logs is denied.") -> None:
        super().__init__(message)


class AuditLogValidationError(DomainError):
    code = "AUDIT_LOG_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
