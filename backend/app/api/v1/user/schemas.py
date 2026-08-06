"""User Management request/response schemas (users.md)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.domain.enums.user_status import UserStatus


class UserCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int = Field(..., ge=1)
    email: EmailStr
    password: str = Field(..., min_length=12, max_length=128)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    role_id: int | None = Field(default=None, ge=1)
    role_name: str | None = Field(default=None, max_length=100)
    username: str | None = Field(default=None, max_length=100)
    employee_id: str | None = Field(default=None, max_length=50)
    display_name: str | None = Field(default=None, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=500)
    department: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=100)
    language: str = Field(default="en", max_length=20)
    timezone: str = Field(default="UTC", max_length=100)
    status: UserStatus = UserStatus.ACTIVE
    is_email_verified: bool = False

    @model_validator(mode="after")
    def require_role(self) -> UserCreateRequest:
        if self.role_id is None and not self.role_name:
            raise ValueError("role_id or role_name is required")
        return self


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=2, max_length=100)
    last_name: str | None = Field(default=None, min_length=2, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    username: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=500)
    department: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=100)
    employee_id: str | None = Field(default=None, max_length=50)
    language: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=100)
    status: UserStatus | None = None
    is_email_verified: bool | None = None


class UserProfileUpdateRequest(BaseModel):
    """Owner self-service profile update (`PUT /users/me`)."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=2, max_length=100)
    last_name: str | None = Field(default=None, min_length=2, max_length=100)
    display_name: str | None = Field(default=None, max_length=150)
    username: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    avatar_url: str | None = Field(default=None, max_length=500)
    department: str | None = Field(default=None, max_length=100)
    job_title: str | None = Field(default=None, max_length=100)
    language: str | None = Field(default=None, max_length=20)
    timezone: str | None = Field(default=None, max_length=100)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=12, max_length=128)


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    new_password: str = Field(..., min_length=12, max_length=128)
    force_change_on_next_login: bool = True


class AssignRolesRequest(BaseModel):
    """Single-role model: assign exactly one role (users.md Rule 3)."""

    model_config = ConfigDict(extra="forbid")

    role_id: int | None = Field(default=None, ge=1)
    role_name: str | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def require_role(self) -> AssignRolesRequest:
        if self.role_id is None and not self.role_name:
            raise ValueError("role_id or role_name is required")
        return self


class AssignCompanyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: int = Field(..., ge=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    company_id: int
    role_id: int
    role_name: str | None = None
    username: str | None = None
    employee_id: str | None = None
    first_name: str
    last_name: str
    display_name: str | None = None
    email: EmailStr
    phone: str | None = None
    avatar_url: str | None = None
    department: str | None = None
    job_title: str | None = None
    language: str
    timezone: str
    status: UserStatus
    is_email_verified: bool
    must_change_password: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None


class UserProfileResponse(UserResponse):
    """Authenticated caller's profile (same fields; semantic alias)."""


class UserListResponse(BaseModel):
    """Paginated list envelope content (items + meta via Page)."""

    model_config = ConfigDict(from_attributes=True)

    items: list[UserResponse]
