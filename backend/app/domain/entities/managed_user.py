"""Full user domain entity for User Management (extends auth-facing AuthUser)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.enums.user_status import UserStatus


@dataclass(slots=True)
class ManagedUser:
    """Complete user profile used by the User Management module."""

    user_id: int
    company_id: int
    role_id: int
    email: str
    first_name: str
    last_name: str
    status: UserStatus
    is_email_verified: bool
    failed_login_attempts: int
    language: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    username: str | None = None
    employee_id: str | None = None
    display_name: str | None = None
    phone: str | None = None
    avatar_url: str | None = None
    department: str | None = None
    job_title: str | None = None
    email_verified_at: datetime | None = None
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    must_change_password: bool = False
    password_changed_at: datetime | None = None
    deleted_at: datetime | None = None
    role_name: str | None = None

    @property
    def is_super_admin(self) -> bool:
        return (self.role_name or "").upper() == "SUPER_ADMIN"

    @property
    def is_company_admin(self) -> bool:
        return (self.role_name or "").upper() == "COMPANY_ADMIN"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
