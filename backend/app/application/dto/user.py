"""User management DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.domain.enums.user_status import UserStatus


@dataclass(slots=True)
class CreateUserInput:
    company_id: int
    email: str
    password: str
    first_name: str
    last_name: str
    role_id: int | None = None
    role_name: str | None = None
    username: str | None = None
    employee_id: str | None = None
    display_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    department: str | None = None
    job_title: str | None = None
    language: str = "en"
    timezone: str = "UTC"
    status: UserStatus = UserStatus.ACTIVE
    is_email_verified: bool = False


@dataclass(slots=True)
class UpdateUserInput:
    """Partial update via ``values`` (supports explicit null clears)."""

    values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UpdateProfileInput:
    first_name: str | None = None
    last_name: str | None = None
    display_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    department: str | None = None
    job_title: str | None = None
    language: str | None = None
    timezone: str | None = None
    username: str | None = None


@dataclass(slots=True)
class ChangePasswordInput:
    current_password: str
    new_password: str


@dataclass(slots=True)
class ResetPasswordInput:
    new_password: str
    force_change_on_next_login: bool = True


@dataclass(slots=True)
class AssignRoleInput:
    role_id: int | None = None
    role_name: str | None = None


@dataclass(slots=True)
class AssignCompanyInput:
    company_id: int


@dataclass(slots=True)
class UserListQuery:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    status: UserStatus | None = None
    role_id: int | None = None
    company_id: int | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    include_deleted: bool = False
