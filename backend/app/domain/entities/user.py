"""Authenticated user domain entity (auth-focused subset)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.domain.enums.user_status import UserStatus


@dataclass(slots=True)
class AuthUser:
    """User fields required for authentication and authorization."""

    user_id: int
    company_id: int
    role_id: int
    email: str
    password_hash: str
    first_name: str
    last_name: str
    status: UserStatus
    is_email_verified: bool
    failed_login_attempts: int
    created_at: datetime
    updated_at: datetime
    role_name: str | None = None
    display_name: str | None = None
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    deleted_at: datetime | None = None
    permissions: frozenset[str] = field(default_factory=frozenset)

    @property
    def is_super_admin(self) -> bool:
        return (self.role_name or "").upper() == "SUPER_ADMIN"

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
