"""User Management repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.entities.managed_user import ManagedUser
from app.domain.enums.user_status import UserStatus


class UserRepository(ABC):
    """Persistence port for user management. No business rules."""

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> ManagedUser:
        ...

    @abstractmethod
    async def get_by_id(
        self,
        user_id: int,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        ...

    @abstractmethod
    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        ...

    @abstractmethod
    async def get_by_username(
        self,
        username: str,
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        ...

    @abstractmethod
    async def update(
        self,
        user_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> ManagedUser | None:
        ...

    @abstractmethod
    async def soft_delete(self, user_id: int, *, at: datetime) -> ManagedUser | None:
        ...

    @abstractmethod
    async def restore(self, user_id: int) -> ManagedUser | None:
        ...

    @abstractmethod
    async def search(
        self,
        *,
        search: str | None,
        status: UserStatus | None,
        role_id: int | None,
        company_id: int | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[ManagedUser], int]:
        ...

    @abstractmethod
    async def count_by_company(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int:
        ...

    @abstractmethod
    async def count_active_company_admins(
        self,
        company_id: int,
        *,
        exclude_user_id: int | None = None,
    ) -> int:
        ...

    @abstractmethod
    async def get_role_id_by_name(self, role_name: str) -> int | None:
        ...

    @abstractmethod
    async def get_role_name(self, role_id: int) -> str | None:
        ...

    @abstractmethod
    async def get_password_hash(self, user_id: int) -> str | None:
        """Return stored password hash for verification (never expose via API)."""
        ...
