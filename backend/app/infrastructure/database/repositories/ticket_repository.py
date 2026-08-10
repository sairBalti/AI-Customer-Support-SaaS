"""SQLAlchemy ticket repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.ticket import Ticket
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketStatus
from app.domain.interfaces.repositories.ticket_repository import TicketRepository
from app.infrastructure.database.mappers.ticket_mapper import ticket_to_entity
from app.infrastructure.database.models.ticket import TicketModel

_SORTABLE = {
    "created_at": TicketModel.created_at,
    "updated_at": TicketModel.updated_at,
    "priority": TicketModel.priority,
    "status": TicketModel.status,
    "ticket_id": TicketModel.ticket_id,
}


class SQLAlchemyTicketRepository(TicketRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> Ticket:
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        for key in ("status", "priority", "category", "source"):
            if key in payload and hasattr(payload[key], "value"):
                payload[key] = payload[key].value
        model = TicketModel(**payload)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return ticket_to_entity(model)

    async def get_by_id(
        self,
        ticket_id: int,
        *,
        company_id: int | None = None,
    ) -> Ticket | None:
        stmt = select(TicketModel).where(TicketModel.ticket_id == ticket_id)
        if company_id is not None:
            stmt = stmt.where(TicketModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return ticket_to_entity(model) if model else None

    async def list_filtered(
        self,
        *,
        company_id: int,
        customer_id: int | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: TicketCategory | None = None,
        assigned_to: int | None = None,
        conversation_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Ticket], int]:
        filters = [TicketModel.company_id == company_id]
        if customer_id is not None:
            filters.append(TicketModel.customer_id == customer_id)
        if status is not None:
            filters.append(TicketModel.status == status.value)
        if priority is not None:
            filters.append(TicketModel.priority == priority.value)
        if category is not None:
            filters.append(TicketModel.category == category.value)
        if assigned_to is not None:
            filters.append(TicketModel.assigned_to == assigned_to)
        if conversation_id is not None:
            filters.append(TicketModel.conversation_id == conversation_id)

        count_stmt = select(func.count()).select_from(TicketModel).where(*filters)
        total = int((await self._session.execute(count_stmt)).scalar_one())

        sort_col = _SORTABLE.get(sort_by, TicketModel.created_at)
        order = desc(sort_col) if sort_order.lower() != "asc" else asc(sort_col)
        offset = max(page - 1, 0) * page_size
        stmt = select(TicketModel).where(*filters).order_by(order).limit(page_size).offset(offset)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [ticket_to_entity(r) for r in rows], total

    async def update(
        self,
        ticket_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> Ticket | None:
        stmt = select(TicketModel).where(TicketModel.ticket_id == ticket_id)
        if company_id is not None:
            stmt = stmt.where(TicketModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        for key in ("status", "priority", "category", "source"):
            if key in payload and hasattr(payload[key], "value"):
                payload[key] = payload[key].value
        for key, value in payload.items():
            setattr(model, key, value)
        await self._session.flush()
        await self._session.refresh(model)
        return ticket_to_entity(model)

    async def count_by_company(self, company_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(TicketModel)
            .where(TicketModel.company_id == company_id)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def get_by_conversation(
        self,
        conversation_id: int,
        *,
        company_id: int | None = None,
    ) -> Ticket | None:
        stmt = select(TicketModel).where(TicketModel.conversation_id == conversation_id)
        if company_id is not None:
            stmt = stmt.where(TicketModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return ticket_to_entity(model) if model else None
