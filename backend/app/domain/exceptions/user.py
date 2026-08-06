"""User-management domain exceptions."""

from app.domain.exceptions.base import DomainError


class UserNotFoundError(DomainError):
    code = "USER_NOT_FOUND"

    def __init__(self, message: str = "User not found.") -> None:
        super().__init__(message)


class UserConflictError(DomainError):
    code = "USER_CONFLICT"

    def __init__(self, message: str = "User already exists.") -> None:
        super().__init__(message)


class UserValidationError(DomainError):
    code = "USER_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class UserAccessDeniedError(DomainError):
    code = "USER_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this user is denied.") -> None:
        super().__init__(message)


class UserOperationForbiddenError(DomainError):
    code = "USER_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)
