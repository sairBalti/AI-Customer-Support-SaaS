"""Audit log use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.audit import AuditListQuery
from app.application.services.audit.audit_log_service import AuditLogService
from app.core.pagination import Page
from app.domain.entities.audit_log import AuditLog


class ListAuditLogsUseCase:
    def __init__(self, session: AsyncSession, service: AuditLogService) -> None:
        self._db = session
        self._service = service

    async def execute(self, query: AuditListQuery, actor: RequestActor) -> Page[AuditLog]:
        return await self._service.list_logs(query, actor)


class GetAuditLogUseCase:
    def __init__(self, session: AsyncSession, service: AuditLogService) -> None:
        self._db = session
        self._service = service

    async def execute(self, audit_log_id: int, actor: RequestActor) -> AuditLog:
        return await self._service.get_log(audit_log_id, actor)
