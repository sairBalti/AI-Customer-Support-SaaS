"""Create-ticket tool — opens a ticket and auto-routes it to support staff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.context import RequestActor
from app.application.dto.ticket import CreateTicketInput, EscalateConversationInput
from app.application.services.ticket.ticket_service import TicketService
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource


@dataclass(slots=True)
class CreateTicketToolContext:
    """Runtime dependencies injected by the agent / API layer."""

    tickets: TicketService
    actor: RequestActor


def _parse_priority(value: str | None) -> TicketPriority:
    if not value:
        return TicketPriority.MEDIUM
    try:
        return TicketPriority(value.upper())
    except ValueError:
        return TicketPriority.MEDIUM


def _parse_category(value: str | None) -> TicketCategory:
    if not value:
        return TicketCategory.GENERAL
    try:
        return TicketCategory(value.upper())
    except ValueError:
        return TicketCategory.GENERAL


async def create_ticket(
    ctx: CreateTicketToolContext,
    *,
    subject: str,
    description: str,
    conversation_id: int | None = None,
    source_message_id: int | None = None,
    customer_id: int | None = None,
    priority: str | None = None,
    category: str | None = None,
    auto_route: bool = True,
) -> dict[str, Any]:
    """Create a support ticket (from chat when ``conversation_id`` is set).

    Auto-routing assigns the least-loaded ``SUPPORT_AGENT`` (then
    ``SUPPORT_MANAGER``) in the company. Returns a JSON-serializable result.
    """
    pri = _parse_priority(priority)
    cat = _parse_category(category)

    if conversation_id is not None:
        ticket = await ctx.tickets.create_from_conversation(
            conversation_id,
            EscalateConversationInput(
                subject=subject,
                description=description,
                priority=pri,
                category=cat,
                source_message_id=source_message_id,
            ),
            ctx.actor,
        )
    else:
        ticket = await ctx.tickets.create_ticket(
            CreateTicketInput(
                subject=subject,
                description=description,
                priority=pri,
                category=cat,
                conversation_id=None,
                source_message_id=source_message_id,
                customer_id=customer_id,
                source=TicketSource.AI_CHAT,
                auto_route=auto_route,
            ),
            ctx.actor,
        )

    return {
        "ticket_id": ticket.ticket_id,
        "ticket_number": ticket.ticket_number,
        "assigned_to": ticket.assigned_to,
        "status": ticket.status.value,
        "priority": ticket.priority.value,
        "category": ticket.category.value,
        "source": ticket.source.value,
        "conversation_id": ticket.conversation_id,
        "routed": ticket.assigned_to is not None,
    }
