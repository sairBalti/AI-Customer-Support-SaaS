"""Authentication / RBAC related exceptions."""

from app.domain.exceptions.base import DomainError


class AuthenticationError(DomainError):
    code = "AUTHENTICATION_FAILED"

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(message)


class InvalidCredentialsError(AuthenticationError):
    code = "INVALID_CREDENTIALS"

    def __init__(self, message: str = "Invalid email or password.") -> None:
        super().__init__(message)


class TokenInvalidError(AuthenticationError):
    code = "INVALID_TOKEN"

    def __init__(self, message: str = "Authentication token is invalid.") -> None:
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    code = "TOKEN_EXPIRED"

    def __init__(self, message: str = "Authentication token has expired.") -> None:
        super().__init__(message)


class AccountLockedError(AuthenticationError):
    code = "ACCOUNT_LOCKED"

    def __init__(self, message: str = "Account is temporarily locked.") -> None:
        super().__init__(message)


class AccountInactiveError(AuthenticationError):
    code = "ACCOUNT_INACTIVE"

    def __init__(self, message: str = "Account is not allowed to sign in.") -> None:
        super().__init__(message)


class InsufficientPermissionError(DomainError):
    code = "INSUFFICIENT_PERMISSION"

    def __init__(self, message: str = "You do not have permission to perform this action.") -> None:
        super().__init__(message)


class RefreshTokenInvalidError(AuthenticationError):
    code = "INVALID_REFRESH_TOKEN"

    def __init__(self, message: str = "Refresh token is invalid or revoked.") -> None:
        super().__init__(message)
