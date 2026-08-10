"""Integration tests for tickets and chat escalation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import hash_password
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.models.auth import UserModel
from app.infrastructure.database.models.company import CompanyModel
from app.infrastructure.database.seed_rbac import seed_rbac


@pytest.fixture
async def ticket_seed(db_session: AsyncSession) -> dict:
    roles = await seed_rbac(db_session)
    company_a = CompanyModel(
        company_name="Ticket A",
        company_slug="ticket-a",
        email="ops@ticket-a.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    company_b = CompanyModel(
        company_name="Ticket B",
        company_slug="ticket-b",
        email="ops@ticket-b.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add_all([company_a, company_b])
    await db_session.flush()
    password = "Str0ng!Password"
    hashed = hash_password(password)
    users = {
        "admin_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["COMPANY_ADMIN"],
            first_name="Ada",
            last_name="Admin",
            email="admin@ticket-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "manager_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["SUPPORT_MANAGER"],
            first_name="Mia",
            last_name="Manager",
            email="manager@ticket-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "agent_a": UserModel(
            company_id=company_a.company_id,
            role_id=roles["SUPPORT_AGENT"],
            first_name="Eve",
            last_name="Agent",
            email="agent@ticket-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "cust_a1": UserModel(
            company_id=company_a.company_id,
            role_id=roles["CUSTOMER"],
            first_name="Ann",
            last_name="Customer",
            email="cust1@ticket-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "cust_a2": UserModel(
            company_id=company_a.company_id,
            role_id=roles["CUSTOMER"],
            first_name="Bob",
            last_name="Customer",
            email="cust2@ticket-a.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "cust_b": UserModel(
            company_id=company_b.company_id,
            role_id=roles["CUSTOMER"],
            first_name="Ben",
            last_name="Customer",
            email="cust@ticket-b.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
    }
    db_session.add_all(list(users.values()))
    await db_session.commit()
    return {
        "password": password,
        "emails": {k: v.email for k, v in users.items()},
        "user_ids": {k: int(v.user_id) for k, v in users.items()},
    }


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _token(api_client: AsyncClient, email: str, password: str) -> str:
    resp = await api_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


@pytest.mark.asyncio
async def test_ticket_crud_assign_resolve_close(
    api_client: AsyncClient,
    ticket_seed: dict,
) -> None:
    admin = await _token(api_client, ticket_seed["emails"]["admin_a"], ticket_seed["password"])
    agent = await _token(api_client, ticket_seed["emails"]["agent_a"], ticket_seed["password"])
    cust1 = await _token(api_client, ticket_seed["emails"]["cust_a1"], ticket_seed["password"])
    cust2 = await _token(api_client, ticket_seed["emails"]["cust_a2"], ticket_seed["password"])
    cust_b = await _token(api_client, ticket_seed["emails"]["cust_b"], ticket_seed["password"])

    created = await api_client.post(
        "/api/v1/tickets",
        headers=_auth(cust1),
        json={
            "subject": "Cannot login",
            "description": "Password reset fails",
            "priority": "HIGH",
            "category": "ACCOUNT",
        },
    )
    assert created.status_code == 201, created.text
    ticket_id = created.json()["data"]["ticket_id"]
    assert created.json()["data"]["status"] == "OPEN"

    listed = await api_client.get("/api/v1/tickets", headers=_auth(admin))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] >= 1

    denied_other_customer = await api_client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=_auth(cust2),
    )
    assert denied_other_customer.status_code == 403

    denied_cross_company = await api_client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=_auth(cust_b),
    )
    assert denied_cross_company.status_code == 403

    got = await api_client.get(f"/api/v1/tickets/{ticket_id}", headers=_auth(cust1))
    assert got.status_code == 200

    updated = await api_client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=_auth(agent),
        json={"priority": "URGENT"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["data"]["priority"] == "URGENT"

    denied_agent_assign = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=_auth(agent),
        json={"assigned_to": ticket_seed["user_ids"]["agent_a"]},
    )
    assert denied_agent_assign.status_code == 403

    assigned = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        headers=_auth(admin),
        json={"assigned_to": ticket_seed["user_ids"]["agent_a"]},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["data"]["status"] == "IN_PROGRESS"

    resolved = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/resolve",
        headers=_auth(agent),
    )
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "RESOLVED"
    assert resolved.json()["data"]["resolved_at"] is not None

    denied_agent_close = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/close",
        headers=_auth(agent),
    )
    assert denied_agent_close.status_code == 403

    closed = await api_client.post(
        f"/api/v1/tickets/{ticket_id}/close",
        headers=_auth(admin),
    )
    assert closed.status_code == 200
    assert closed.json()["data"]["status"] == "CLOSED"
    assert closed.json()["data"]["closed_at"] is not None


@pytest.mark.asyncio
async def test_escalate_from_chat_conversation(
    api_client: AsyncClient,
    ticket_seed: dict,
) -> None:
    cust = await _token(api_client, ticket_seed["emails"]["cust_a1"], ticket_seed["password"])
    cust_b = await _token(api_client, ticket_seed["emails"]["cust_b"], ticket_seed["password"])

    conversation = await api_client.post(
        "/api/v1/chat/conversations",
        headers=_auth(cust),
        json={"title": "Need help"},
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["data"]["conversation_id"]

    escalated = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/ticket",
        headers=_auth(cust),
        json={
            "subject": "Human needed",
            "description": "AI could not help",
            "priority": "MEDIUM",
            "category": "TECHNICAL",
        },
    )
    assert escalated.status_code == 201, escalated.text
    data = escalated.json()["data"]
    assert data["conversation_id"] == conversation_id
    assert data["source"] == "AI_CHAT"
    assert data["status"] == "OPEN"

    denied = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/ticket",
        headers=_auth(cust_b),
        json={"description": "stolen"},
    )
    assert denied.status_code in {403, 404}

    conflict = await api_client.post(
        f"/api/v1/chat/conversations/{conversation_id}/ticket",
        headers=_auth(cust),
        json={"description": "again"},
    )
    assert conflict.status_code == 409
