"""SQLAlchemy audit log repository (append-only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.audit_log import AuditLog
from app.domain.interfaces.repositories.audit_log_repository import AuditLogRepository
from app.infrastructure.database.mappers.audit_log_mapper import audit_log_to_entity
from app.infrastructure.database.models.audit_log import AuditLogModel


class SQLAlchemyAuditLogRepository(AuditLogRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> AuditLog:
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        model = AuditLogModel(**payload)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return audit_log_to_entity(model)

    async def get_by_id(
        self,
        audit_log_id: int,
        *,
        company_id: int | None = None,
    ) -> AuditLog | None:
        stmt = select(AuditLogModel).where(AuditLogModel.audit_log_id == audit_log_id)
        if company_id is not None:
            stmt = stmt.where(AuditLogModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return audit_log_to_entity(model) if model else None

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
    ) -> tuple[list[AuditLog], int]:
        filters = []
        if company_id is not None:
            filters.append(AuditLogModel.company_id == company_id)
        if actor_user_id is not None:
            filters.append(AuditLogModel.actor_user_id == actor_user_id)
        if action is not None:
            filters.append(AuditLogModel.action == action)
        if entity_type is not None:
            filters.append(AuditLogModel.entity_type == entity_type)
        if entity_id is not None:
            filters.append(AuditLogModel.entity_id == entity_id)
        if from_date is not None:
            filters.append(AuditLogModel.created_at >= from_date)
        if to_date is not None:
            filters.append(AuditLogModel.created_at <= to_date)

        count_stmt = select(func.count()).select_from(AuditLogModel)
        if filters:
            count_stmt = count_stmt.where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one())

        order = (
            desc(AuditLogModel.created_at)
            if sort_order.lower() != "asc"
            else asc(AuditLogModel.created_at)
        )
        offset = max(page - 1, 0) * page_size
        stmt = select(AuditLogModel)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.order_by(order).limit(page_size).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [audit_log_to_entity(r) for r in rows], total
