"""Ticket application service — human escalation / support tickets."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.application.context import RequestActor
from app.application.dto.ticket import (
    AssignTicketInput,
    CreateTicketInput,
    EscalateConversationInput,
    TicketListQuery,
    UpdateTicketInput,
)
from app.core.pagination import Page
from app.core.security.rbac import ensure_permissions
from app.domain.entities.ticket import Ticket
from app.domain.enums.chat_status import ChatSessionStatus
from app.domain.enums.ticket_status import TicketSource, TicketStatus
from app.domain.exceptions.chat import ChatAccessDeniedError, ChatNotFoundError
from app.domain.exceptions.ticket import (
    TicketAccessDeniedError,
    TicketConflictError,
    TicketNotFoundError,
    TicketOperationForbiddenError,
    TicketValidationError,
)
from app.domain.interfaces.repositories.chat_message_repository import ChatMessageRepository
from app.domain.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.domain.interfaces.repositories.ticket_repository import TicketRepository
from app.domain.interfaces.repositories.user_repository import UserRepository
from app.domain.interfaces.services.audit_logger import AuditLogger

_ALLOWED_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    TicketStatus.OPEN: frozenset(
        {TicketStatus.IN_PROGRESS, TicketStatus.RESOLVED, TicketStatus.CLOSED}
    ),
    TicketStatus.IN_PROGRESS: frozenset(
        {TicketStatus.OPEN, TicketStatus.RESOLVED, TicketStatus.CLOSED}
    ),
    TicketStatus.RESOLVED: frozenset({TicketStatus.CLOSED, TicketStatus.IN_PROGRESS}),
    TicketStatus.CLOSED: frozenset(),
}


class TicketService:
    def __init__(
        self,
        *,
        tickets: TicketRepository,
        users: UserRepository,
        sessions: ChatSessionRepository,
        messages: ChatMessageRepository,
        audit_logger: AuditLogger,
    ) -> None:
        self._tickets = tickets
        self._users = users
        self._sessions = sessions
        self._messages = messages
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        """Persist queued audit events on the current session before commit."""
        if not self._pending_audits:
            return
        events = list(self._pending_audits)
        for event in events:
            await self._audit.log(**event)
        self._pending_audits.clear()

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def create_ticket(self, data: CreateTicketInput, actor: RequestActor) -> Ticket:
        ensure_permissions(actor, "tickets.create")
        company_id = self._require_company_id(actor)
        subject = (data.subject or "").strip()
        description = (data.description or "").strip()
        if not subject:
            raise TicketValidationError("subject is required.")
        if not description:
            raise TicketValidationError("description is required.")

        customer_id = data.customer_id
        if self._is_customer(actor):
            customer_id = actor.user_id
        if customer_id is None:
            raise TicketValidationError("customer_id is required.")

        await self._assert_user_in_company(int(customer_id), company_id)

        if data.conversation_id is not None:
            session = await self._sessions.get_by_id(
                data.conversation_id,
                company_id=company_id,
            )
            if session is None:
                raise TicketValidationError("conversation_id is invalid for this company.")
            if self._is_customer(actor) and session.customer_id != actor.user_id:
                raise TicketAccessDeniedError(
                    "Customers may only escalate their own conversations."
                )
            existing = await self._tickets.get_by_conversation(
                data.conversation_id,
                company_id=company_id,
            )
            if existing is not None:
                raise TicketConflictError("A ticket already exists for this conversation.")

        if data.source_message_id is not None:
            message = await self._messages.get_by_id(
                data.source_message_id,
                company_id=company_id,
            )
            if message is None:
                raise TicketValidationError("source_message_id is invalid for this company.")
            if data.conversation_id is not None and message.session_id != data.conversation_id:
                raise TicketValidationError(
                    "source_message_id does not belong to the given conversation."
                )

        now = datetime.now(UTC)
        count = await self._tickets.count_by_company(company_id)
        ticket_number = f"SUP-{now.year}-{company_id:04d}-{count + 1:06d}"
        ticket = await self._tickets.create(
            {
                "company_id": company_id,
                "customer_id": int(customer_id),
                "conversation_id": data.conversation_id,
                "source_message_id": data.source_message_id,
                "ticket_number": ticket_number,
                "subject": subject[:255],
                "description": description,
                "category": data.category,
                "priority": data.priority,
                "status": TicketStatus.OPEN,
                "source": data.source,
                "created_at": now,
                "updated_at": now,
                "metadata": {},
            }
        )
        self._queue_audit(
            action="tickets.create",
            entity_id=ticket.ticket_id,
            company_id=company_id,
            user_id=actor.user_id,
        )
        return ticket

    async def list_tickets(
        self,
        query: TicketListQuery,
        actor: RequestActor,
    ) -> Page[Ticket]:
        ensure_permissions(actor, "tickets.read")
        company_id = self._require_company_id(actor)
        customer_id = query.customer_id
        if self._is_customer(actor):
            customer_id = actor.user_id
        items, total = await self._tickets.list_filtered(
            company_id=company_id,
            customer_id=customer_id,
            status=query.status,
            priority=query.priority,
            category=query.category,
            assigned_to=query.assigned_to,
            conversation_id=query.conversation_id,
            page=query.page,
            page_size=query.page_size,
            sort_by=query.sort_by,
            sort_order=query.sort_order,
        )
        return Page.of(
            items,
            page=query.page,
            page_size=query.page_size,
            total_items=total,
        )

    async def get_ticket(self, ticket_id: int, actor: RequestActor) -> Ticket:
        ensure_permissions(actor, "tickets.read")
        return await self._load_ticket_for_actor(ticket_id, actor)

    async def update_ticket(
        self,
        ticket_id: int,
        data: UpdateTicketInput,
        actor: RequestActor,
    ) -> Ticket:
        ensure_permissions(actor, "tickets.update")
        ticket = await self._load_ticket_for_actor(ticket_id, actor, require_staff=True)
        if ticket.is_closed:
            raise TicketOperationForbiddenError("Closed tickets cannot be modified.")

        updates: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if data.subject is not None:
            subject = data.subject.strip()
            if not subject:
                raise TicketValidationError("subject cannot be empty.")
            updates["subject"] = subject[:255]
        if data.description is not None:
            description = data.description.strip()
            if not description:
                raise TicketValidationError("description cannot be empty.")
            updates["description"] = description
        if data.priority is not None:
            updates["priority"] = data.priority
        if data.category is not None:
            updates["category"] = data.category
        if data.status is not None and data.status != ticket.status:
            self._assert_transition(ticket.status, data.status)
            updates["status"] = data.status
            if data.status == TicketStatus.RESOLVED:
                updates["resolved_at"] = datetime.now(UTC)
            if data.status == TicketStatus.CLOSED:
                updates["closed_at"] = datetime.now(UTC)
                if ticket.resolved_at is None:
                    updates["resolved_at"] = datetime.now(UTC)

        updated = await self._tickets.update(
            ticket.ticket_id,
            updates,
            company_id=ticket.company_id,
        )
        assert updated is not None
        self._queue_audit(
            action="tickets.update",
            entity_id=ticket.ticket_id,
            company_id=ticket.company_id,
            user_id=actor.user_id,
        )
        return updated

    async def assign_ticket(
        self,
        ticket_id: int,
        data: AssignTicketInput,
        actor: RequestActor,
    ) -> Ticket:
        ensure_permissions(actor, "tickets.assign")
        ticket = await self._load_ticket_for_actor(ticket_id, actor, require_staff=True)
        if ticket.is_closed:
            raise TicketOperationForbiddenError("Closed tickets cannot be assigned.")
        await self._assert_user_in_company(data.assigned_to, ticket.company_id)

        updates: dict[str, Any] = {
            "assigned_to": data.assigned_to,
            "updated_at": datetime.now(UTC),
        }
        if ticket.status == TicketStatus.OPEN:
            updates["status"] = TicketStatus.IN_PROGRESS
        updated = await self._tickets.update(
            ticket.ticket_id,
            updates,
            company_id=ticket.company_id,
        )
        assert updated is not None
        self._queue_audit(
            action="tickets.assign",
            entity_id=ticket.ticket_id,
            company_id=ticket.company_id,
            user_id=actor.user_id,
            metadata={"assigned_to": data.assigned_to},
        )
        return updated

    async def resolve_ticket(self, ticket_id: int, actor: RequestActor) -> Ticket:
        ensure_permissions(actor, "tickets.resolve")
        ticket = await self._load_ticket_for_actor(ticket_id, actor, require_staff=True)
        if ticket.is_closed:
            raise TicketOperationForbiddenError("Closed tickets cannot be resolved.")
        if ticket.status == TicketStatus.RESOLVED:
            return ticket
        self._assert_transition(ticket.status, TicketStatus.RESOLVED)
        now = datetime.now(UTC)
        updated = await self._tickets.update(
            ticket.ticket_id,
            {
                "status": TicketStatus.RESOLVED,
                "resolved_at": now,
                "updated_at": now,
            },
            company_id=ticket.company_id,
        )
        assert updated is not None
        self._queue_audit(
            action="tickets.resolve",
            entity_id=ticket.ticket_id,
            company_id=ticket.company_id,
            user_id=actor.user_id,
        )
        return updated

    async def close_ticket(self, ticket_id: int, actor: RequestActor) -> Ticket:
        ensure_permissions(actor, "tickets.close")
        ticket = await self._load_ticket_for_actor(ticket_id, actor, require_staff=True)
        if ticket.status == TicketStatus.CLOSED:
            return ticket
        self._assert_transition(ticket.status, TicketStatus.CLOSED)
        now = datetime.now(UTC)
        updates: dict[str, Any] = {
            "status": TicketStatus.CLOSED,
            "closed_at": now,
            "updated_at": now,
        }
        if ticket.resolved_at is None:
            updates["resolved_at"] = now
        updated = await self._tickets.update(
            ticket.ticket_id,
            updates,
            company_id=ticket.company_id,
        )
        assert updated is not None
        self._queue_audit(
            action="tickets.close",
            entity_id=ticket.ticket_id,
            company_id=ticket.company_id,
            user_id=actor.user_id,
        )
        return updated

    async def create_from_conversation(
        self,
        conversation_id: int,
        data: EscalateConversationInput,
        actor: RequestActor,
    ) -> Ticket:
        """Escalate a chat conversation into a support ticket."""
        ensure_permissions(actor, "tickets.create")
        company_id = self._require_company_id(actor)
        session = await self._sessions.get_by_id(conversation_id, company_id=company_id)
        if session is None:
            other = await self._sessions.get_by_id(conversation_id)
            if other is not None and other.company_id != company_id:
                raise ChatAccessDeniedError(
                    "Cannot access a conversation belonging to another company.",
                )
            raise ChatNotFoundError()
        if self._is_customer(actor) and session.customer_id != actor.user_id:
            raise ChatAccessDeniedError("Customers may only escalate their own conversations.")

        existing = await self._tickets.get_by_conversation(
            conversation_id,
            company_id=company_id,
        )
        if existing is not None or session.ticket_id is not None:
            raise TicketConflictError("A ticket already exists for this conversation.")

        subject = (data.subject or session.title or "Support escalation").strip()
        description = (data.description or "").strip()
        if not description:
            description = f"Escalated from conversation {session.session_uuid}."

        ticket = await self.create_ticket(
            CreateTicketInput(
                subject=subject,
                description=description,
                priority=data.priority,
                category=data.category,
                conversation_id=conversation_id,
                source_message_id=data.source_message_id,
                customer_id=session.customer_id,
                source=TicketSource.AI_CHAT,
            ),
            actor,
        )
        await self._sessions.update(
            conversation_id,
            {
                "ticket_id": ticket.ticket_id,
                "escalation_required": True,
                "escalated_at": datetime.now(UTC),
                "session_status": ChatSessionStatus.ESCALATED,
                "updated_at": datetime.now(UTC),
            },
            company_id=company_id,
        )
        self._queue_audit(
            action="tickets.escalate_from_chat",
            entity_id=ticket.ticket_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={"conversation_id": conversation_id},
        )
        return ticket

    async def _load_ticket_for_actor(
        self,
        ticket_id: int,
        actor: RequestActor,
        *,
        require_staff: bool = False,
    ) -> Ticket:
        company_id = self._require_company_id(actor)
        ticket = await self._tickets.get_by_id(ticket_id, company_id=company_id)
        if ticket is None:
            other = await self._tickets.get_by_id(ticket_id)
            if other is not None and other.company_id != company_id:
                raise TicketAccessDeniedError(
                    "Cannot access a ticket belonging to another company.",
                )
            raise TicketNotFoundError()
        if require_staff and self._is_customer(actor):
            raise TicketAccessDeniedError("Customers cannot perform this ticket action.")
        if self._is_customer(actor) and ticket.customer_id != actor.user_id:
            raise TicketAccessDeniedError("Customers may only access their own tickets.")
        return ticket

    async def _assert_user_in_company(self, user_id: int, company_id: int) -> None:
        user = await self._users.get_by_id(user_id)
        if user is None or user.company_id != company_id:
            raise TicketValidationError("User must belong to the same company.")

    @staticmethod
    def _assert_transition(current: TicketStatus, new: TicketStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS.get(current, frozenset())
        if new not in allowed:
            raise TicketOperationForbiddenError(
                f"Invalid status transition from {current.value} to {new.value}.",
            )

    def _require_company_id(self, actor: RequestActor) -> int:
        if actor.company_id is None:
            raise TicketValidationError("company context is required.")
        return int(actor.company_id)

    @staticmethod
    def _is_customer(actor: RequestActor) -> bool:
        return (actor.role_name or "").upper() == "CUSTOMER"

    def _queue_audit(
        self,
        *,
        action: str,
        entity_id: int,
        company_id: int | None,
        user_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._pending_audits.append(
            {
                "action": action,
                "entity": "ticket",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
