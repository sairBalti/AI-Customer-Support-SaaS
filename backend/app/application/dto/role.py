"""Role management DTOs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CreateRoleInput:
    role_name: str
    display_name: str
    description: str | None = None
    company_id: int | None = None
    is_system_role: bool = False
    is_active: bool = True
    sort_order: int = 0


@dataclass(slots=True)
class UpdateRoleInput:
    values: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RoleListQuery:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    company_id: int | None = None
    include_global: bool = True
    is_system_role: bool | None = None
    is_active: bool | None = None
    sort_by: str = "sort_order"
    sort_order: str = "asc"
    include_deleted: bool = False
