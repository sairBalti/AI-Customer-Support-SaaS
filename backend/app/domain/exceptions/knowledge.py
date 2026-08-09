"""Knowledge Base / RAG domain exceptions."""

from app.domain.exceptions.base import DomainError


class KnowledgeNotFoundError(DomainError):
    code = "KNOWLEDGE_NOT_FOUND"

    def __init__(self, message: str = "Knowledge resource not found.") -> None:
        super().__init__(message)


class KnowledgeValidationError(DomainError):
    code = "KNOWLEDGE_VALIDATION_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class KnowledgeAccessDeniedError(DomainError):
    code = "KNOWLEDGE_ACCESS_DENIED"

    def __init__(self, message: str = "Access to knowledge is denied.") -> None:
        super().__init__(message)


class KnowledgeOperationForbiddenError(DomainError):
    code = "KNOWLEDGE_OPERATION_FORBIDDEN"

    def __init__(self, message: str) -> None:
        super().__init__(message)


class KnowledgeProcessingError(DomainError):
    code = "KNOWLEDGE_PROCESSING_ERROR"

    def __init__(self, message: str) -> None:
        super().__init__(message)
