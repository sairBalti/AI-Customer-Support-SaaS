"""Unit tests for TicketService."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.ticket import (
    AssignTicketInput,
    CreateTicketInput,
    EscalateConversationInput,
    TicketListQuery,
    UpdateTicketInput,
)
from app.application.services.ticket.ticket_service import TicketService
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.managed_user import ManagedUser
from app.domain.entities.ticket import Ticket
from app.domain.enums.chat_status import ChatSessionStatus
from app.domain.enums.ticket_priority import TicketPriority
from app.domain.enums.ticket_status import TicketCategory, TicketSource, TicketStatus
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.ticket import (
    TicketAccessDeniedError,
    TicketConflictError,
    TicketOperationForbiddenError,
    TicketValidationError,
)


class _TicketRepo:
    def __init__(self) -> None:
        self.rows: dict[int, Ticket] = {}
        self._next = 1

    async def create(self, data: dict[str, Any]) -> Ticket:
        now = datetime.now(UTC)
        tid = self._next
        self._next += 1
        ticket = Ticket(
            ticket_id=tid,
            company_id=int(data["company_id"]),
            customer_id=int(data["customer_id"]),
            ticket_number=data["ticket_number"],
            subject=data["subject"],
            description=data["description"],
            priority=data["priority"],
            status=data["status"],
            category=data["category"],
            source=data["source"],
            created_at=data.get("created_at", now),
            updated_at=data.get("updated_at", now),
            conversation_id=data.get("conversation_id"),
            source_message_id=data.get("source_message_id"),
            assigned_to=data.get("assigned_to"),
            metadata={},
        )
        self.rows[tid] = ticket
        return ticket

    async def get_by_id(self, ticket_id: int, *, company_id: int | None = None) -> Ticket | None:
        ticket = self.rows.get(ticket_id)
        if ticket is None:
            return None
        if company_id is not None and ticket.company_id != company_id:
            return None
        return ticket

    async def list_filtered(self, **kwargs: Any) -> tuple[list[Ticket], int]:
        company_id = kwargs["company_id"]
        items = [t for t in self.rows.values() if t.company_id == company_id]
        if kwargs.get("customer_id") is not None:
            items = [t for t in items if t.customer_id == kwargs["customer_id"]]
        if kwargs.get("status") is not None:
            items = [t for t in items if t.status == kwargs["status"]]
        if kwargs.get("assigned_to") is not None:
            items = [t for t in items if t.assigned_to == kwargs["assigned_to"]]
        return items, len(items)

    async def update(
        self,
        ticket_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> Ticket | None:
        ticket = await self.get_by_id(ticket_id, company_id=company_id)
        if ticket is None:
            return None
        for key, value in data.items():
            object.__setattr__(ticket, key, value)
        return ticket

    async def count_by_company(self, company_id: int) -> int:
        return sum(1 for t in self.rows.values() if t.company_id == company_id)

    async def count_active_by_assignee(
        self,
        *,
        company_id: int,
        assignee_ids: Sequence[int],
    ) -> dict[int, int]:
        active = {TicketStatus.OPEN, TicketStatus.IN_PROGRESS}
        counts = {uid: 0 for uid in assignee_ids}
        for ticket in self.rows.values():
            if (
                ticket.company_id == company_id
                and ticket.assigned_to in counts
                and ticket.status in active
            ):
                counts[ticket.assigned_to] += 1
        return counts

    async def get_by_conversation(
        self,
        conversation_id: int,
        *,
        company_id: int | None = None,
    ) -> Ticket | None:
        for ticket in self.rows.values():
            if ticket.conversation_id == conversation_id and (
                company_id is None or ticket.company_id == company_id
            ):
                return ticket
        return None


class _UserRepo:
    def __init__(
        self,
        users: dict[int, ManagedUser],
        *,
        roles: dict[str, int] | None = None,
    ) -> None:
        self.users = users
        self.roles = roles or {}

    async def get_by_id(self, user_id: int, *, include_deleted: bool = False) -> ManagedUser | None:
        _ = include_deleted
        return self.users.get(user_id)

    async def get_role_id_by_name(self, role_name: str) -> int | None:
        return self.roles.get(role_name.upper())

    async def search(self, **kwargs: Any) -> tuple[list[ManagedUser], int]:
        company_id = kwargs.get("company_id")
        role_id = kwargs.get("role_id")
        status = kwargs.get("status")
        items = list(self.users.values())
        if company_id is not None:
            items = [u for u in items if u.company_id == company_id]
        if role_id is not None:
            items = [u for u in items if u.role_id == role_id]
        if status is not None:
            items = [u for u in items if u.status == status]
        items.sort(key=lambda u: u.user_id)
        return items, len(items)


class _SessionRepo:
    def __init__(self, sessions: dict[int, ChatSession] | None = None) -> None:
        self.sessions = sessions or {}

    async def get_by_id(
        self, session_id: int, *, company_id: int | None = None
    ) -> ChatSession | None:
        session = self.sessions.get(session_id)
        if session is None:
            return None
        if company_id is not None and session.company_id != company_id:
            return None
        return session

    async def update(
        self,
        session_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> ChatSession | None:
        session = await self.get_by_id(session_id, company_id=company_id)
        if session is None:
            return None
        for key, value in data.items():
            object.__setattr__(session, key, value)
        return session


class _MessageRepo:
    async def get_by_id(self, message_id: int, *, company_id: int | None = None) -> None:
        _ = message_id, company_id
        return None


class _Audit:
    async def log(self, **kwargs: Any) -> None:
        _ = kwargs


def _user(
    user_id: int,
    company_id: int,
    *,
    role_id: int = 1,
    role_name: str | None = None,
) -> ManagedUser:
    now = datetime.now(UTC)
    return ManagedUser(
        user_id=user_id,
        company_id=company_id,
        role_id=role_id,
        first_name="T",
        last_name="U",
        email=f"u{user_id}@ex.com",
        status=UserStatus.ACTIVE,
        language="en",
        timezone="UTC",
        is_email_verified=True,
        failed_login_attempts=0,
        must_change_password=False,
        created_at=now,
        updated_at=now,
        role_name=role_name,
    )


def _session(session_id: int, company_id: int, customer_id: int) -> ChatSession:
    now = datetime.now(UTC)
    return ChatSession(
        session_id=session_id,
        company_id=company_id,
        customer_id=customer_id,
        session_uuid="uuid",
        language="en",
        ai_provider="fake",
        ai_model="fake",
        session_status=ChatSessionStatus.ACTIVE,
        total_messages=0,
        total_prompt_tokens=0,
        total_completion_tokens=0,
        total_tokens=0,
        estimated_cost=Decimal("0"),
        escalation_required=False,
        created_at=now,
        updated_at=now,
        title="Help",
    )


def _service(
    *,
    tickets: _TicketRepo | None = None,
    users: dict[int, ManagedUser] | None = None,
    sessions: dict[int, ChatSession] | None = None,
    roles: dict[str, int] | None = None,
) -> TicketService:
    return TicketService(
        tickets=tickets or _TicketRepo(),
        users=_UserRepo(
            users or {1: _user(1, 1), 2: _user(2, 1), 9: _user(9, 2)},
            roles=roles,
        ),
        sessions=_SessionRepo(sessions or {}),
        messages=_MessageRepo(),
        audit_logger=_Audit(),
    )


def _admin() -> RequestActor:
    return RequestActor(
        user_id=2,
        company_id=1,
        role_name="COMPANY_ADMIN",
        permissions=frozenset(
            {
                "tickets.create",
                "tickets.read",
                "tickets.update",
                "tickets.assign",
                "tickets.resolve",
                "tickets.close",
            }
        ),
    )


@pytest.mark.asyncio
async def test_create_and_status_workflow() -> None:
    service = _service()
    admin = _admin()
    ticket = await service.create_ticket(
        CreateTicketInput(
            subject="Billing issue",
            description="Cannot pay invoice",
            priority=TicketPriority.HIGH,
            category=TicketCategory.BILLING,
            customer_id=1,
        ),
        admin,
    )
    assert ticket.status == TicketStatus.OPEN
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.assigned_to is None

    assigned = await service.assign_ticket(
        ticket.ticket_id,
        AssignTicketInput(assigned_to=2),
        admin,
    )
    assert assigned.status == TicketStatus.IN_PROGRESS
    assert assigned.assigned_to == 2

    resolved = await service.resolve_ticket(ticket.ticket_id, admin)
    assert resolved.status == TicketStatus.RESOLVED
    assert resolved.resolved_at is not None

    closed = await service.close_ticket(ticket.ticket_id, admin)
    assert closed.status == TicketStatus.CLOSED
    assert closed.closed_at is not None

    with pytest.raises(TicketOperationForbiddenError):
        await service.update_ticket(
            ticket.ticket_id,
            UpdateTicketInput(subject="Nope"),
            admin,
        )


@pytest.mark.asyncio
async def test_invalid_transition_and_isolation() -> None:
    service = _service()
    admin = RequestActor(
        user_id=2,
        company_id=1,
        role_name="SUPPORT_MANAGER",
        permissions=frozenset(
            {"tickets.create", "tickets.read", "tickets.close", "tickets.resolve"}
        ),
    )
    ticket = await service.create_ticket(
        CreateTicketInput(subject="X", description="Y", customer_id=1),
        admin,
    )
    await service.close_ticket(ticket.ticket_id, admin)

    outsider = RequestActor(
        user_id=9,
        company_id=2,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.read", "tickets.create"}),
    )
    with pytest.raises(TicketAccessDeniedError):
        await service.get_ticket(ticket.ticket_id, outsider)

    customer = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.read", "tickets.create"}),
    )
    assert (await service.get_ticket(ticket.ticket_id, customer)).ticket_id == ticket.ticket_id

    other_customer = RequestActor(
        user_id=3,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.read"}),
    )
    users = {1: _user(1, 1), 2: _user(2, 1), 3: _user(3, 1)}
    service2 = _service(tickets=service._tickets, users=users)  # type: ignore[arg-type]
    with pytest.raises(TicketAccessDeniedError):
        await service2.get_ticket(ticket.ticket_id, other_customer)


@pytest.mark.asyncio
async def test_escalate_from_conversation() -> None:
    sessions = {10: _session(10, 1, 1)}
    service = _service(sessions=sessions)
    customer = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.create", "tickets.read"}),
    )
    ticket = await service.create_from_conversation(
        10,
        EscalateConversationInput(subject="Need a human", description="AI failed"),
        customer,
    )
    assert ticket.conversation_id == 10
    assert ticket.source == TicketSource.AI_CHAT
    assert sessions[10].ticket_id == ticket.ticket_id
    assert sessions[10].session_status == ChatSessionStatus.ESCALATED

    with pytest.raises(TicketConflictError):
        await service.create_from_conversation(
            10,
            EscalateConversationInput(description="again"),
            customer,
        )


@pytest.mark.asyncio
async def test_customer_list_only_own() -> None:
    service = _service()
    admin = RequestActor(
        user_id=2,
        company_id=1,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"tickets.create", "tickets.read"}),
    )
    await service.create_ticket(
        CreateTicketInput(subject="A", description="A", customer_id=1),
        admin,
    )
    customer = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.read"}),
    )
    page = await service.list_tickets(TicketListQuery(), customer)
    assert page.meta.total_items == 1


@pytest.mark.asyncio
async def test_validation_errors() -> None:
    service = _service()
    actor = RequestActor(
        user_id=2,
        company_id=1,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"tickets.create"}),
    )
    with pytest.raises(TicketValidationError):
        await service.create_ticket(
            CreateTicketInput(subject=" ", description="x", customer_id=1),
            actor,
        )


@pytest.mark.asyncio
async def test_auto_routes_to_least_loaded_agent() -> None:
    agent_role = 40
    users = {
        1: _user(1, 1, role_id=1, role_name="CUSTOMER"),
        2: _user(2, 1, role_id=2, role_name="COMPANY_ADMIN"),
        10: _user(10, 1, role_id=agent_role, role_name="SUPPORT_AGENT"),
        11: _user(11, 1, role_id=agent_role, role_name="SUPPORT_AGENT"),
    }
    service = _service(
        users=users,
        roles={"SUPPORT_AGENT": agent_role, "SUPPORT_MANAGER": 30},
    )
    admin = _admin()
    first = await service.create_ticket(
        CreateTicketInput(subject="A", description="A", customer_id=1),
        admin,
    )
    assert first.assigned_to == 10
    assert first.status == TicketStatus.IN_PROGRESS

    second = await service.create_ticket(
        CreateTicketInput(subject="B", description="B", customer_id=1),
        admin,
    )
    assert second.assigned_to == 11

    third = await service.create_ticket(
        CreateTicketInput(subject="C", description="C", customer_id=1),
        admin,
    )
    assert third.assigned_to == 10


@pytest.mark.asyncio
async def test_auto_route_can_be_disabled() -> None:
    agent_role = 40
    users = {
        1: _user(1, 1),
        2: _user(2, 1),
        10: _user(10, 1, role_id=agent_role, role_name="SUPPORT_AGENT"),
    }
    service = _service(users=users, roles={"SUPPORT_AGENT": agent_role})
    ticket = await service.create_ticket(
        CreateTicketInput(
            subject="No route",
            description="keep open",
            customer_id=1,
            auto_route=False,
        ),
        _admin(),
    )
    assert ticket.assigned_to is None
    assert ticket.status == TicketStatus.OPEN


@pytest.mark.asyncio
async def test_escalate_auto_routes_for_customer() -> None:
    agent_role = 40
    sessions = {10: _session(10, 1, 1)}
    users = {
        1: _user(1, 1, role_name="CUSTOMER"),
        10: _user(10, 1, role_id=agent_role, role_name="SUPPORT_AGENT"),
    }
    service = _service(
        sessions=sessions,
        users=users,
        roles={"SUPPORT_AGENT": agent_role},
    )
    customer = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.create", "tickets.read"}),
    )
    ticket = await service.create_from_conversation(
        10,
        EscalateConversationInput(subject="Need a human", description="AI failed"),
        customer,
    )
    assert ticket.assigned_to == 10
    assert ticket.status == TicketStatus.IN_PROGRESS
