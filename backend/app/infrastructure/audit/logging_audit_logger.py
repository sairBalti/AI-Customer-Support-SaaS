"""Structured logging audit adapter (DB audit_logs wiring comes later)."""

from __future__ import annotations

import logging
from typing import Any

from app.domain.interfaces.services.audit_logger import AuditLogger

logger = logging.getLogger("app.audit")


class LoggingAuditLogger(AuditLogger):
    """Best-effort audit hook that emits structured log events."""

    async def log(
        self,
        *,
        action: str,
        entity: str,
        entity_id: int | str | None,
        company_id: int | None,
        user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            logger.info(
                "audit_event",
                extra={
                    "audit_action": action,
                    "audit_entity": entity,
                    "audit_entity_id": entity_id,
                    "audit_company_id": company_id,
                    "audit_user_id": user_id,
                    "audit_metadata": metadata or {},
                },
            )
        except Exception:  # noqa: BLE001 — audit must never break the request
            logger.exception("Failed to emit audit event")
