"""Ticket & human escalation API router."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.api.deps import DbSession, TicketServiceDep
from app.api.security import (
    RequireTicketAssign,
    RequireTicketClose,
    RequireTicketCreate,
    RequireTicketRead,
    RequireTicketResolve,
    RequireTicketUpdate,
)
from app.api.v1.ticket.schemas import (
    AssignTicketRequest,
    CreateTicketRequest,
    TicketResponse,
    UpdateTicketRequest,
)
from app.application.dto.ticket import (
    AssignTicketInput,
    CreateTicketInput,
    TicketListQuery,
    UpdateTicketInput,
)
from app.application.use_cases.ticket import (
    AssignTicketUseCase,
    CloseTicketUseCase,
    CreateTicketUseCase,
    GetTicketUseCase,
    ListTicketsUseCase,
    ResolveTicketUseCase,
    UpdateTicketUseCase,
)
from app.core.responses.envelopes import success_envelope
from app.domain.entities.ticket import Ticket
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource, TicketStatus

router = APIRouter(prefix="/tickets", tags=["Tickets"])

_AUTH_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"description": "Missing or invalid JWT"},
    403: {"description": "Insufficient permission or tenant isolation"},
    404: {"description": "Ticket not found"},
}


def _to_response(ticket: Ticket) -> dict[str, Any]:
    return TicketResponse(
        ticket_id=ticket.ticket_id,
        ticket_number=ticket.ticket_number,
        company_id=ticket.company_id,
        customer_id=ticket.customer_id,
        conversation_id=ticket.conversation_id,
        source_message_id=ticket.source_message_id,
        assigned_to=ticket.assigned_to,
        subject=ticket.subject,
        description=ticket.description,
        status=ticket.status,
        priority=ticket.priority,
        category=ticket.category,
        source=ticket.source.value,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
    ).model_dump(mode="json")


@router.post(
    "",
    summary="Create support ticket",
    status_code=201,
    responses=_AUTH_RESPONSES,
)
async def create_ticket(
    body: CreateTicketRequest,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketCreate,
) -> dict[str, Any]:
    ticket = await CreateTicketUseCase(session, service).execute(
        CreateTicketInput(
            subject=body.subject,
            description=body.description,
            priority=body.priority,
            category=body.category,
            conversation_id=body.conversation_id,
            source_message_id=body.source_message_id,
            customer_id=body.customer_id,
            source=TicketSource.MANUAL,
        ),
        actor,
    )
    return success_envelope(_to_response(ticket), message="Ticket created.")


@router.get(
    "",
    summary="List tickets",
    responses=_AUTH_RESPONSES,
)
async def list_tickets(
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketRead,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_filter: Annotated[
        TicketStatus | None,
        Query(alias="status"),
    ] = None,
    priority: Annotated[TicketPriority | None, Query()] = None,
    category: Annotated[TicketCategory | None, Query()] = None,
    assigned_to: Annotated[int | None, Query()] = None,
    customer_id: Annotated[int | None, Query()] = None,
    conversation_id: Annotated[int | None, Query()] = None,
    sort_by: Annotated[str, Query()] = "created_at",
    sort_order: Annotated[str, Query()] = "desc",
) -> dict[str, Any]:
    page_result = await ListTicketsUseCase(session, service).execute(
        TicketListQuery(
            page=page,
            page_size=page_size,
            status=status_filter,
            priority=priority,
            category=category,
            assigned_to=assigned_to,
            customer_id=customer_id,
            conversation_id=conversation_id,
            sort_by=sort_by,
            sort_order=sort_order,
        ),
        actor,
    )
    return success_envelope(
        {
            "items": [_to_response(t) for t in page_result.items],
            "meta": page_result.meta.model_dump(mode="json"),
        }
    )


@router.get(
    "/{ticket_id}",
    summary="Get ticket",
    responses=_AUTH_RESPONSES,
)
async def get_ticket(
    ticket_id: int,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketRead,
) -> dict[str, Any]:
    ticket = await GetTicketUseCase(session, service).execute(ticket_id, actor)
    return success_envelope(_to_response(ticket))


@router.patch(
    "/{ticket_id}",
    summary="Update ticket",
    responses=_AUTH_RESPONSES,
)
async def update_ticket(
    ticket_id: int,
    body: UpdateTicketRequest,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketUpdate,
) -> dict[str, Any]:
    ticket = await UpdateTicketUseCase(session, service).execute(
        ticket_id,
        UpdateTicketInput(
            subject=body.subject,
            description=body.description,
            priority=body.priority,
            category=body.category,
            status=body.status,
        ),
        actor,
    )
    return success_envelope(_to_response(ticket), message="Ticket updated.")


@router.post(
    "/{ticket_id}/assign",
    summary="Assign ticket",
    responses=_AUTH_RESPONSES,
)
async def assign_ticket(
    ticket_id: int,
    body: AssignTicketRequest,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketAssign,
) -> dict[str, Any]:
    ticket = await AssignTicketUseCase(session, service).execute(
        ticket_id,
        AssignTicketInput(assigned_to=body.assigned_to),
        actor,
    )
    return success_envelope(_to_response(ticket), message="Ticket assigned.")


@router.post(
    "/{ticket_id}/resolve",
    summary="Resolve ticket",
    responses=_AUTH_RESPONSES,
)
async def resolve_ticket(
    ticket_id: int,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketResolve,
) -> dict[str, Any]:
    ticket = await ResolveTicketUseCase(session, service).execute(ticket_id, actor)
    return success_envelope(_to_response(ticket), message="Ticket resolved.")


@router.post(
    "/{ticket_id}/close",
    summary="Close ticket",
    responses=_AUTH_RESPONSES,
)
async def close_ticket(
    ticket_id: int,
    session: DbSession,
    service: TicketServiceDep,
    actor: RequireTicketClose,
) -> dict[str, Any]:
    ticket = await CloseTicketUseCase(session, service).execute(ticket_id, actor)
    return success_envelope(_to_response(ticket), message="Ticket closed.")
