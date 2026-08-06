"""Auth request/response schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1)


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(..., min_length=20)


class LogoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str | None = None
    revoke_all: bool = False


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthUserResponse(BaseModel):
    user_id: int
    company_id: int
    email: EmailStr
    first_name: str
    last_name: str
    display_name: str | None = None
    role_name: str | None = None
    permissions: list[str] = Field(default_factory=list)
    is_super_admin: bool = False


class LoginResponseData(BaseModel):
    tokens: TokenResponse
    user: AuthUserResponse
