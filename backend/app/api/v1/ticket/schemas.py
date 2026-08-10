"""Ticket API request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketStatus


class CreateTicketRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=50_000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL
    conversation_id: int | None = None
    source_message_id: int | None = None
    customer_id: int | None = None


class UpdateTicketRequest(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1, max_length=50_000)
    priority: TicketPriority | None = None
    category: TicketCategory | None = None
    status: TicketStatus | None = None


class AssignTicketRequest(BaseModel):
    assigned_to: int = Field(ge=1)


class EscalateConversationRequest(BaseModel):
    subject: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=50_000)
    priority: TicketPriority = TicketPriority.MEDIUM
    category: TicketCategory = TicketCategory.GENERAL
    source_message_id: int | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticket_id: int
    ticket_number: str
    company_id: int
    customer_id: int
    conversation_id: int | None = None
    source_message_id: int | None = None
    assigned_to: int | None = None
    subject: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    source: str
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
