"""Ticket application use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.ticket import (
    AssignTicketInput,
    CreateTicketInput,
    EscalateConversationInput,
    TicketListQuery,
    UpdateTicketInput,
)
from app.application.services.ticket.ticket_service import TicketService
from app.core.pagination import Page
from app.domain.entities.ticket import Ticket


class CreateTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(self, data: CreateTicketInput, actor: RequestActor) -> Ticket:
        try:
            result = await self._tickets.create_ticket(data, actor)
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise


class ListTicketsUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(self, query: TicketListQuery, actor: RequestActor) -> Page[Ticket]:
        return await self._tickets.list_tickets(query, actor)


class GetTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(self, ticket_id: int, actor: RequestActor) -> Ticket:
        return await self._tickets.get_ticket(ticket_id, actor)


class UpdateTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(
        self,
        ticket_id: int,
        data: UpdateTicketInput,
        actor: RequestActor,
    ) -> Ticket:
        try:
            result = await self._tickets.update_ticket(ticket_id, data, actor)
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise


class AssignTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(
        self,
        ticket_id: int,
        data: AssignTicketInput,
        actor: RequestActor,
    ) -> Ticket:
        try:
            result = await self._tickets.assign_ticket(ticket_id, data, actor)
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise


class ResolveTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(self, ticket_id: int, actor: RequestActor) -> Ticket:
        try:
            result = await self._tickets.resolve_ticket(ticket_id, actor)
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise


class CloseTicketUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(self, ticket_id: int, actor: RequestActor) -> Ticket:
        try:
            result = await self._tickets.close_ticket(ticket_id, actor)
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise


class EscalateConversationUseCase:
    def __init__(self, session: AsyncSession, service: TicketService) -> None:
        self._db = session
        self._tickets = service

    async def execute(
        self,
        conversation_id: int,
        data: EscalateConversationInput,
        actor: RequestActor,
    ) -> Ticket:
        try:
            result = await self._tickets.create_from_conversation(
                conversation_id,
                data,
                actor,
            )
            await self._db.commit()
            await self._tickets.flush_audits()
            return result
        except Exception:
            self._tickets.discard_audits()
            await self._db.rollback()
            raise
