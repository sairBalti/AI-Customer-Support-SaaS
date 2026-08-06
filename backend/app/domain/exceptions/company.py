"""Company domain exceptions."""

from app.domain.exceptions.base import DomainError


class CompanyNotFoundError(DomainError):
    """Raised when a company cannot be found."""

    code = "COMPANY_NOT_FOUND"

    def __init__(self, message: str = "Company not found.") -> None:
        super().__init__(message)


class CompanyConflictError(DomainError):
    """Raised when a unique company constraint is violated."""

    code = "COMPANY_CONFLICT"

    def __init__(self, message: str = "Company already exists.") -> None:
        super().__init__(message)


class CompanyValidationError(DomainError):
    """Raised when company input fails domain validation."""

    code = "COMPANY_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CompanyAccessDeniedError(DomainError):
    """Raised when tenant isolation forbids the action."""

    code = "COMPANY_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this company is denied.") -> None:
        super().__init__(message)


class CompanyOperationForbiddenError(DomainError):
    """Raised when an operation is not allowed for the caller's role."""

    code = "COMPANY_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class CompanyInactiveError(DomainError):
    """Raised when the caller's company cannot use protected APIs."""

    code = "COMPANY_INACTIVE"

    def __init__(
        self,
        message: str = "Company is inactive and cannot access this resource.",
    ) -> None:
        super().__init__(message)
