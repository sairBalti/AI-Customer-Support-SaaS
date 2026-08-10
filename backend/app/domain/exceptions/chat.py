"""Chat / AI support agent domain exceptions."""

from app.domain.exceptions.base import DomainError


class ChatNotFoundError(DomainError):
    code = "CHAT_NOT_FOUND"

    def __init__(self, message: str = "Conversation not found.") -> None:
        super().__init__(message)


class ChatValidationError(DomainError):
    code = "CHAT_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class ChatAccessDeniedError(DomainError):
    code = "CHAT_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this conversation is denied.") -> None:
        super().__init__(message)


class ChatOperationForbiddenError(DomainError):
    code = "CHAT_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)
