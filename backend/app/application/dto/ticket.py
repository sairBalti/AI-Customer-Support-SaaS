"""Ticket application DTOs."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource, TicketStatus


@dataclass(slots=True)
class CreateTicketInput:
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL
    conversation_id: int | None = None
    source_message_id: int | None = None
    customer_id: int | None = None
    source: TicketSource = TicketSource.MANUAL


@dataclass(slots=True)
class UpdateTicketInput:
    subject: str | None = None
    description: str | None = None
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    status: TicketStatus | None = None


@dataclass(slots=True)
class AssignTicketInput:
    assigned_to: int


@dataclass(slots=True)
class TicketListQuery:
    page: int = 1
    page_size: int = 20
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    assigned_to: int | None = None
    customer_id: int | None = None
    conversation_id: int | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"


@dataclass(slots=True)
class EscalateConversationInput:
    subject: str | None = None
    description: str | None = None
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL
    source_message_id: int | None = None
