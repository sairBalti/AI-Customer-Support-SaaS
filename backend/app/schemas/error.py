"""Standard error response schema."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured API error payload."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = False
    error: ErrorDetail


class SuccessResponse(BaseModel):
    """Standard success envelope."""

    success: bool = True
    data: Any = None
    message: str | None = Field(default=None)
