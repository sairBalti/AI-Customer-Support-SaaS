"""Audit log domain entity (append-only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class AuditLog:
    audit_log_id: int
    company_id: int
    action: str
    entity_type: str
    created_at: datetime
    actor_user_id: int | None = None
    entity_id: int | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    audit_uuid: str | None = None
