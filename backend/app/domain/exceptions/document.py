"""Document-management domain exceptions."""

from app.domain.exceptions.base import DomainError


class DocumentNotFoundError(DomainError):
    code = "DOCUMENT_NOT_FOUND"

    def __init__(self, message: str = "Document not found.") -> None:
        super().__init__(message)


class DocumentConflictError(DomainError):
    code = "DOCUMENT_CONFLICT"

    def __init__(self, message: str = "Document already exists.") -> None:
        super().__init__(message)


class DocumentValidationError(DomainError):
    code = "DOCUMENT_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DocumentAccessDeniedError(DomainError):
    code = "DOCUMENT_ACCESS_DENIED"

    def __init__(self, message: str = "Access to this document is denied.") -> None:
        super().__init__(message)


class DocumentOperationForbiddenError(DomainError):
    code = "DOCUMENT_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)
