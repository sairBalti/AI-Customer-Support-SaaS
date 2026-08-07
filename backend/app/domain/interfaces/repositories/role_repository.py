"""Role Management repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.entities.role import Role


class RoleRepository(ABC):
    """Persistence port for roles. No business rules."""

    @abstractmethod
    async def create(self, data: dict[str, Any]) -> Role: ...

    @abstractmethod
    async def get_by_id(
        self,
        role_id: int,
        *,
        include_deleted: bool = False,
    ) -> Role | None: ...

    @abstractmethod
    async def get_by_name(
        self,
        role_name: str,
        *,
        company_id: int | None = None,
        include_deleted: bool = False,
    ) -> Role | None:
        """Resolve role by name within company scope (or global when company_id is None)."""

    @abstractmethod
    async def update(
        self,
        role_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Role | None: ...

    @abstractmethod
    async def soft_delete(self, role_id: int, *, at: datetime) -> Role | None: ...

    @abstractmethod
    async def restore(self, role_id: int) -> Role | None: ...

    @abstractmethod
    async def search(
        self,
        *,
        search: str | None,
        company_id: int | None,
        include_global: bool,
        is_system_role: bool | None,
        is_active: bool | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[Role], int]: ...

    @abstractmethod
    async def count_users_with_role(self, role_id: int) -> int: ...

    @abstractmethod
    async def count_role_permissions(self, role_id: int) -> int: ...
