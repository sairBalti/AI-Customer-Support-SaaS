"""Auth-oriented user repository port (not a User CRUD API)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from app.domain.entities.user import AuthUser


class AuthUserRepository(ABC):
    """Read/update operations required by the authentication module."""

    @abstractmethod
    async def get_by_email(self, email: str) -> AuthUser | None:
        """Fetch a non-deleted user by login email, including role name."""

    @abstractmethod
    async def get_by_id(self, user_id: int) -> AuthUser | None:
        """Fetch a non-deleted user by id, including role name + permissions."""

    @abstractmethod
    async def get_permissions_for_role(self, role_id: int) -> frozenset[str]:
        """Return permission names granted to a role."""

    @abstractmethod
    async def record_login_success(
        self,
        user_id: int,
        *,
        ip_address: str | None,
        at: datetime,
    ) -> None:
        """Reset failure counters and stamp last login."""

    @abstractmethod
    async def record_login_failure(
        self,
        user_id: int,
        *,
        failed_login_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        """Persist failed-login bookkeeping."""
