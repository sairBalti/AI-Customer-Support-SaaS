"""Ticket repository port."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities.ticket import Ticket
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketStatus


class TicketRepository(Protocol):
    async def create(self, data: dict[str, Any]) -> Ticket: ...

    async def get_by_id(
        self,
        ticket_id: int,
        *,
        company_id: int | None = None,
    ) -> Ticket | None: ...

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
    ) -> tuple[list[Ticket], int]: ...

    async def update(
        self,
        ticket_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> Ticket | None: ...

    async def count_by_company(self, company_id: int) -> int: ...

    async def get_by_conversation(
        self,
        conversation_id: int,
        *,
        company_id: int | None = None,
    ) -> Ticket | None: ...
