"""Ticket domain entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource, TicketStatus


@dataclass(slots=True)
class Ticket:
    ticket_id: int
    company_id: int
    customer_id: int
    ticket_number: str
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    category: TicketCategory
    source: TicketSource
    created_at: datetime
    updated_at: datetime
    conversation_id: int | None = None
    source_message_id: int | None = None
    assigned_to: int | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_closed(self) -> bool:
        return self.status == TicketStatus.CLOSED

    @property
    def is_modifiable(self) -> bool:
        return self.status != TicketStatus.CLOSED
