"""Audit log application service (read + explicit record helper)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.application.context import RequestActor
from app.application.dto.audit import AuditListQuery, RecordAuditInput
from app.core.audit_sanitize import sanitize_audit_metadata
from app.core.pagination import Page
from app.core.security.rbac import ensure_permissions
from app.domain.entities.audit_log import AuditLog
from app.domain.exceptions.audit import AuditLogAccessDeniedError, AuditLogNotFoundError
from app.domain.interfaces.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    def __init__(self, *, audit_logs: AuditLogRepository) -> None:
        self._audit_logs = audit_logs

    async def record(self, data: RecordAuditInput) -> AuditLog:
        """Explicit application-level record (not used by read APIs)."""
        return await self._audit_logs.create(
            {
                "company_id": data.company_id,
                "actor_user_id": data.actor_user_id,
                "audit_uuid": str(uuid.uuid4()),
                "action": data.action,
                "entity_type": data.entity_type,
                "entity_id": data.entity_id,
                "description": data.description,
                "metadata": sanitize_audit_metadata(data.metadata),
                "ip_address": data.ip_address,
                "user_agent": data.user_agent,
                "created_at": datetime.now(UTC),
            }
        )

    async def list_logs(self, query: AuditListQuery, actor: RequestActor) -> Page[AuditLog]:
        ensure_permissions(actor, "audit.read")
        company_id = self._resolve_company_id(query.company_id, actor)
        items, total = await self._audit_logs.list_filtered(
            company_id=company_id,
            actor_user_id=query.actor_user_id,
            action=query.action,
            entity_type=query.entity_type,
            entity_id=query.entity_id,
            from_date=query.from_date,
            to_date=query.to_date,
            page=query.page,
            page_size=query.page_size,
            sort_order=query.sort_order,
        )
        return Page.of(
            items,
            page=query.page,
            page_size=query.page_size,
            total_items=total,
        )

    async def get_log(self, audit_log_id: int, actor: RequestActor) -> AuditLog:
        """Fetch one audit row; foreign/missing IDs both surface as not found."""
        ensure_permissions(actor, "audit.read")
        company_id = None if actor.is_super_admin else self._require_company_id(actor)
        row = await self._audit_logs.get_by_id(audit_log_id, company_id=company_id)
        if row is None:
            # Uniform 404 — do not probe whether the ID exists in another tenant.
            raise AuditLogNotFoundError()
        return row

    def _resolve_company_id(
        self,
        requested: int | None,
        actor: RequestActor,
    ) -> int | None:
        if actor.is_super_admin:
            return requested
        company_id = self._require_company_id(actor)
        if requested is not None and requested != company_id:
            raise AuditLogAccessDeniedError(
                "Cannot query audit logs for another company.",
            )
        return company_id

    @staticmethod
    def _require_company_id(actor: RequestActor) -> int:
        if actor.company_id is None:
            raise AuditLogAccessDeniedError("company context is required.")
        return int(actor.company_id)
