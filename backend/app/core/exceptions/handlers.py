"""FastAPI exception handlers — standardized error envelope."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses.envelopes import error_envelope
from app.domain.exceptions.auth import (
    AccountInactiveError,
    AccountLockedError,
    AuthenticationError,
    InsufficientPermissionError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.domain.exceptions.base import DomainError
from app.domain.exceptions.chat import (
    ChatAccessDeniedError,
    ChatNotFoundError,
    ChatOperationForbiddenError,
    ChatValidationError,
)
from app.domain.exceptions.company import (
    CompanyAccessDeniedError,
    CompanyConflictError,
    CompanyInactiveError,
    CompanyNotFoundError,
    CompanyOperationForbiddenError,
    CompanyValidationError,
)
from app.domain.exceptions.document import (
    DocumentAccessDeniedError,
    DocumentConflictError,
    DocumentNotFoundError,
    DocumentOperationForbiddenError,
    DocumentValidationError,
)
from app.domain.exceptions.knowledge import (
    KnowledgeAccessDeniedError,
    KnowledgeNotFoundError,
    KnowledgeOperationForbiddenError,
    KnowledgeProcessingError,
    KnowledgeValidationError,
)
from app.domain.exceptions.role import (
    RoleAccessDeniedError,
    RoleConflictError,
    RoleNotFoundError,
    RoleOperationForbiddenError,
    RoleValidationError,
)
from app.domain.exceptions.user import (
    UserAccessDeniedError,
    UserConflictError,
    UserNotFoundError,
    UserOperationForbiddenError,
    UserValidationError,
)

logger = logging.getLogger(__name__)

_DOMAIN_STATUS: dict[type[DomainError], int] = {
    CompanyNotFoundError: status.HTTP_404_NOT_FOUND,
    CompanyConflictError: status.HTTP_409_CONFLICT,
    CompanyValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    CompanyAccessDeniedError: status.HTTP_403_FORBIDDEN,
    CompanyOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    CompanyInactiveError: status.HTTP_403_FORBIDDEN,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    UserConflictError: status.HTTP_409_CONFLICT,
    UserValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    UserAccessDeniedError: status.HTTP_403_FORBIDDEN,
    UserOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    RoleNotFoundError: status.HTTP_404_NOT_FOUND,
    RoleConflictError: status.HTTP_409_CONFLICT,
    RoleValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    RoleAccessDeniedError: status.HTTP_403_FORBIDDEN,
    RoleOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
    DocumentConflictError: status.HTTP_409_CONFLICT,
    DocumentValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    DocumentAccessDeniedError: status.HTTP_403_FORBIDDEN,
    DocumentOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    KnowledgeNotFoundError: status.HTTP_404_NOT_FOUND,
    KnowledgeValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    KnowledgeAccessDeniedError: status.HTTP_403_FORBIDDEN,
    KnowledgeOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    KnowledgeProcessingError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ChatNotFoundError: status.HTTP_404_NOT_FOUND,
    ChatValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    ChatAccessDeniedError: status.HTTP_403_FORBIDDEN,
    ChatOperationForbiddenError: status.HTTP_403_FORBIDDEN,
    InsufficientPermissionError: status.HTTP_403_FORBIDDEN,
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    TokenInvalidError: status.HTTP_401_UNAUTHORIZED,
    TokenExpiredError: status.HTTP_401_UNAUTHORIZED,
    RefreshTokenInvalidError: status.HTTP_401_UNAUTHORIZED,
    AccountLockedError: status.HTTP_403_FORBIDDEN,
    AccountInactiveError: status.HTTP_403_FORBIDDEN,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
}


def register_exception_handlers(app: FastAPI) -> None:
    """Attach global exception handlers to the FastAPI app."""

    @app.exception_handler(DomainError)
    async def domain_exception_handler(
        _request: Request,
        exc: DomainError,
    ) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        for exc_type, code in _DOMAIN_STATUS.items():
            if isinstance(exc, exc_type):
                status_code = code
                break
        headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
        body = error_envelope(code=exc.code, message=exc.message)
        return JSONResponse(status_code=status_code, content=body, headers=headers)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            body = error_envelope(
                code=str(detail["code"]),
                message=str(detail["message"]),
                details=detail.get("details"),
            )
        else:
            body = error_envelope(
                code="HTTP_ERROR",
                message=str(detail),
            )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        body = error_envelope(
            code="VALIDATION_ERROR",
            message="Request validation failed.",
            details={"errors": exc.errors()},
        )
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        _request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled server error: %s", exc)
        body = error_envelope(
            code="INTERNAL_SERVER_ERROR",
            message="An unexpected error occurred.",
        )
        return JSONResponse(status_code=500, content=body)
