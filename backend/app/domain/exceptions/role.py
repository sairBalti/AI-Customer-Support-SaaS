"""Role-management domain exceptions."""

from app.domain.exceptions.base import DomainError


class RoleNotFoundError(DomainError):
    code = "ROLE_NOT_FOUND"

    def __init__(self, message: str = "Role not found.") -> None:
        super().__init__(message)


class RoleConflictError(DomainError):
    code = "ROLE_CONFLICT"

    def __init__(self, message: str = "Role already exists.") -> None:
        super().__init__(message)


class RoleValidationError(DomainError):
    code = "ROLE_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class RoleAccessDeniedError(DomainError):
    code = "ROLE_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this role is denied.") -> None:
        super().__init__(message)


class RoleOperationForbiddenError(DomainError):
    code = "ROLE_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)
