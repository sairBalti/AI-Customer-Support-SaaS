"""Audit log API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    audit_log_id: int
    company_id: int
    actor_user_id: int | None = None
    audit_uuid: str | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime
