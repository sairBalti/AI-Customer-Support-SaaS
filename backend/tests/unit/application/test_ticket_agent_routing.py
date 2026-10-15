"""Unit tests for create_ticket tool and ticket LangGraph node."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.agents.langgraph.nodes.ticket import ticket_node
from app.agents.tools.create_ticket import CreateTicketToolContext, create_ticket
from app.application.context import RequestActor
from app.application.services.ticket.ticket_service import TicketService
from app.domain.entities.chat_session import ChatSession
from app.domain.entities.managed_user import ManagedUser
from app.domain.entities.ticket import Ticket
from app.domain.enums.chat_status import ChatSessionStatus
from app.domain.enums.ticket_status import TicketStatus
from app.domain.enums.user_status import UserStatus


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
        items = [t for t in self.rows.values() if t.company_id == kwargs["company_id"]]
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
    def __init__(self, users: dict[int, ManagedUser], roles: dict[str, int]) -> None:
        self.users = users
        self.roles = roles

    async def get_by_id(self, user_id: int, *, include_deleted: bool = False) -> ManagedUser | None:
        _ = include_deleted
        return self.users.get(user_id)

    async def get_role_id_by_name(self, role_name: str) -> int | None:
        return self.roles.get(role_name.upper())

    async def search(self, **kwargs: Any) -> tuple[list[ManagedUser], int]:
        items = [
            u
            for u in self.users.values()
            if u.company_id == kwargs.get("company_id")
            and (kwargs.get("role_id") is None or u.role_id == kwargs["role_id"])
            and (kwargs.get("status") is None or u.status == kwargs["status"])
        ]
        items.sort(key=lambda u: u.user_id)
        return items, len(items)


class _SessionRepo:
    def __init__(self, sessions: dict[int, ChatSession]) -> None:
        self.sessions = sessions

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


def _user(user_id: int, company_id: int, *, role_id: int, role_name: str) -> ManagedUser:
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


def _service() -> tuple[TicketService, dict[int, ChatSession]]:
    agent_role = 40
    sessions = {10: _session(10, 1, 1)}
    users = {
        1: _user(1, 1, role_id=1, role_name="CUSTOMER"),
        10: _user(10, 1, role_id=agent_role, role_name="SUPPORT_AGENT"),
    }
    service = TicketService(
        tickets=_TicketRepo(),
        users=_UserRepo(users, {"SUPPORT_AGENT": agent_role}),
        sessions=_SessionRepo(sessions),
        messages=_MessageRepo(),
        audit_logger=_Audit(),
    )
    return service, sessions


@pytest.mark.asyncio
async def test_create_ticket_tool_escalates_and_routes() -> None:
    service, sessions = _service()
    actor = RequestActor(
        user_id=1,
        company_id=1,
        role_name="CUSTOMER",
        permissions=frozenset({"tickets.create"}),
    )
    result = await create_ticket(
        CreateTicketToolContext(tickets=service, actor=actor),
        subject="Need help",
        description="AI could not answer",
        conversation_id=10,
        priority="HIGH",
    )
    assert result["ticket_id"] == 1
    assert result["assigned_to"] == 10
    assert result["routed"] is True
    assert result["status"] == TicketStatus.IN_PROGRESS.value
    assert sessions[10].ticket_id == 1


@pytest.mark.asyncio
async def test_ticket_node_writes_state() -> None:
    service, _ = _service()
    state = {
        "company_id": 1,
        "user_id": 1,
        "role_name": "CUSTOMER",
        "permissions": ["tickets.create"],
        "conversation_id": 10,
        "should_escalate": True,
        "subject": "Escalate please",
        "description": "Need a human",
    }
    update = await ticket_node(state, tickets=service)  # type: ignore[arg-type]
    assert update["ticket_id"] == 1
    assert update["assigned_to"] == 10
    assert update["error"] is None
