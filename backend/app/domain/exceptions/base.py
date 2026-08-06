"""Base domain exception."""


class DomainError(Exception):
    """Base class for domain-layer errors."""

    code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        self.message = message
        if code is not None:
            self.code = code
        super().__init__(message)
