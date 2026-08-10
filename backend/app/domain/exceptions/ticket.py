"""Ticket domain exceptions."""

from app.domain.exceptions.base import DomainError


class TicketNotFoundError(DomainError):
    code = "TICKET_NOT_FOUND"

    def __init__(self, message: str = "Ticket not found.") -> None:
        super().__init__(message)


class TicketValidationError(DomainError):
    code = "TICKET_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TicketAccessDeniedError(DomainError):
    code = "TICKET_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this ticket is denied.") -> None:
        super().__init__(message)


class TicketOperationForbiddenError(DomainError):
    code = "TICKET_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class TicketConflictError(DomainError):
    code = "TICKET_CONFLICT"

    def __init__(self, message: str) -> None:
        super().__init__(message)
