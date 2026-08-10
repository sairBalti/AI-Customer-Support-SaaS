"""Audit log repository port — create and read only."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from app.domain.entities.audit_log import AuditLog


class AuditLogRepository(Protocol):
    async def create(self, data: dict[str, Any]) -> AuditLog: ...

    async def get_by_id(
        self,
        audit_log_id: int,
        *,
        company_id: int | None = None,
    ) -> AuditLog | None: ...

    async def list_filtered(
        self,
        *,
        company_id: int | None,
        actor_user_id: int | None = None,
        action: str | None = None,
        entity_type: str | None = None,
        entity_id: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_order: str = "desc",
    ) -> tuple[list[AuditLog], int]: ...
