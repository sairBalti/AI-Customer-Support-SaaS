"""Role domain entity for Role Management."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class Role:
    """Hybrid role: global when company_id is None, else company-scoped."""

    role_id: int
    role_name: str
    display_name: str
    is_system_role: bool
    is_active: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime
    company_id: int | None = None
    description: str | None = None
    deleted_at: datetime | None = None

    @property
    def is_system(self) -> bool:
        return self.is_system_role

    @property
    def is_global(self) -> bool:
        return self.company_id is None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
