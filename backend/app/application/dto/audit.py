"""Audit application DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AuditListQuery:
    page: int = 1
    page_size: int = 20
    actor_user_id: int | None = None
    action: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    from_date: datetime | None = None
    to_date: datetime | None = None
    company_id: int | None = None
    sort_order: str = "desc"


@dataclass(slots=True)
class RecordAuditInput:
    company_id: int
    action: str
    entity_type: str
    actor_user_id: int | None = None
    entity_id: int | None = None
    description: str | None = None
    metadata: dict[str, Any] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
