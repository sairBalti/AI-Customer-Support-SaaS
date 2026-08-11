"""Persistent + structured-log audit adapters."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_context import get_audit_request_context
from app.core.audit_sanitize import sanitize_audit_metadata
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.infrastructure.audit.logging_audit_logger import LoggingAuditLogger
from app.infrastructure.database.repositories.audit_log_repository import (
    SQLAlchemyAuditLogRepository,
)


class DatabaseAuditLogger(AuditLogger):
    """Persist audit events on the request AsyncSession (fail-closed).

    Persistence errors propagate so the surrounding business transaction rolls
    back. No separate commit — same session as the mutating use case.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyAuditLogRepository(session)

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
        if company_id is None:
            # Table requires company_id; platform-wide events stay log-only.
            return
        ctx = get_audit_request_context()
        entity_id_int: int | None
        try:
            entity_id_int = int(entity_id) if entity_id is not None else None
        except TypeError, ValueError:
            entity_id_int = None
        await self._repo.create(
            {
                "company_id": int(company_id),
                "actor_user_id": user_id,
                "audit_uuid": str(uuid.uuid4()),
                "action": action,
                "entity_type": entity,
                "entity_id": entity_id_int,
                "description": None,
                "metadata": sanitize_audit_metadata(metadata),
                "ip_address": ctx.ip_address,
                "user_agent": (ctx.user_agent[:2000] if ctx.user_agent else None),
                "created_at": datetime.now(UTC),
            }
        )


class CompositeAuditLogger(AuditLogger):
    """Write structured logs and persist when company_id is present."""

    def __init__(self, session: AsyncSession) -> None:
        self._logging = LoggingAuditLogger()
        self._database = DatabaseAuditLogger(session)

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
        await self._logging.log(
            action=action,
            entity=entity,
            entity_id=entity_id,
            company_id=company_id,
            user_id=user_id,
            metadata=metadata,
        )
        await self._database.log(
            action=action,
            entity=entity,
            entity_id=entity_id,
            company_id=company_id,
            user_id=user_id,
            metadata=metadata,
        )
