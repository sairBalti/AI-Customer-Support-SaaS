"""Map ticket ORM models to domain entities."""

from __future__ import annotations

from app.domain.entities.ticket import Ticket
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource, TicketStatus
from app.infrastructure.database.models.ticket import TicketModel


def ticket_to_entity(model: TicketModel) -> Ticket:
    return Ticket(
        ticket_id=int(model.ticket_id),
        company_id=int(model.company_id),
        customer_id=int(model.customer_id),
        conversation_id=(int(model.conversation_id) if model.conversation_id is not None else None),
        source_message_id=(
            int(model.source_message_id) if model.source_message_id is not None else None
        ),
        assigned_to=int(model.assigned_to) if model.assigned_to is not None else None,
        ticket_number=model.ticket_number,
        subject=model.subject,
        description=model.description,
        category=TicketCategory(model.category),
        priority=TicketPriority(model.priority),
        status=TicketStatus(model.status),
        source=TicketSource(model.source),
        resolved_at=model.resolved_at,
        closed_at=model.closed_at,
        metadata=dict(model.metadata_ or {}),
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
