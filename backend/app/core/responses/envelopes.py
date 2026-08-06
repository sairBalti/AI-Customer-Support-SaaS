"""Standard success/error response envelopes."""

from typing import Any

from app.schemas.error import ErrorDetail, ErrorResponse, SuccessResponse


def success_envelope(data: Any = None, message: str | None = None) -> dict[str, Any]:
    """Build a success response body."""
    return SuccessResponse(data=data, message=message).model_dump()


def error_envelope(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an error response body."""
    return ErrorResponse(
        error=ErrorDetail(code=code, message=message, details=details),
    ).model_dump()
