"""Integration tests for User Management API."""

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
async def user_mgmt_seed(db_session: AsyncSession) -> dict:
    roles = await seed_rbac(db_session)
    company = CompanyModel(
        company_name="User Mgmt Co",
        company_slug="user-mgmt-co",
        email="ops@usermgmt.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    other = CompanyModel(
        company_name="Other Tenant",
        company_slug="other-tenant",
        email="ops@other.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add_all([company, other])
    await db_session.flush()

    password = "Str0ng!Password"
    hashed = hash_password(password)
    admin = UserModel(
        company_id=company.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Cara",
        last_name="Admin",
        email="admin@usermgmt.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    agent = UserModel(
        company_id=company.company_id,
        role_id=roles["SUPPORT_AGENT"],
        first_name="Alice",
        last_name="Agent",
        email="agent@usermgmt.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    super_admin = UserModel(
        company_id=company.company_id,
        role_id=roles["SUPER_ADMIN"],
        first_name="Sue",
        last_name="Root",
        email="super@usermgmt.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add_all([admin, agent, super_admin])
    await db_session.commit()
    return {
        "password": password,
        "company_id": int(company.company_id),
        "other_id": int(other.company_id),
        "roles": roles,
        "emails": {
            "admin": "admin@usermgmt.co",
            "agent": "agent@usermgmt.co",
            "super": "super@usermgmt.co",
        },
    }


async def _token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_company_admin_user_crud_flow(
    api_client: AsyncClient,
    user_mgmt_seed: dict,
) -> None:
    token = await _token(
        api_client,
        user_mgmt_seed["emails"]["admin"],
        user_mgmt_seed["password"],
    )
    create = await api_client.post(
        "/api/v1/users",
        headers=_auth(token),
        json={
            "company_id": user_mgmt_seed["company_id"],
            "email": "new@usermgmt.co",
            "password": "Str0ng!Password",
            "first_name": "New",
            "last_name": "User",
            "role_name": "SUPPORT_AGENT",
            "username": "new.user",
        },
    )
    assert create.status_code == 201, create.text
    user_id = create.json()["data"]["user_id"]
    assert create.json()["data"]["username"] == "new.user"

    listed = await api_client.get("/api/v1/users", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] >= 2

    fetched = await api_client.get(f"/api/v1/users/{user_id}", headers=_auth(token))
    assert fetched.status_code == 200

    patched = await api_client.patch(
        f"/api/v1/users/{user_id}",
        headers=_auth(token),
        json={"department": "Support"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["department"] == "Support"

    deactivated = await api_client.patch(
        f"/api/v1/users/{user_id}/deactivate",
        headers=_auth(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["data"]["status"] == "INACTIVE"

    activated = await api_client.patch(
        f"/api/v1/users/{user_id}/activate",
        headers=_auth(token),
    )
    assert activated.status_code == 200

    deleted = await api_client.delete(f"/api/v1/users/{user_id}", headers=_auth(token))
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None

    restored = await api_client.patch(
        f"/api/v1/users/{user_id}/restore",
        headers=_auth(token),
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["deleted_at"] is None


@pytest.mark.asyncio
async def test_agent_cannot_create_or_delete_users(
    api_client: AsyncClient,
    user_mgmt_seed: dict,
) -> None:
    token = await _token(
        api_client,
        user_mgmt_seed["emails"]["agent"],
        user_mgmt_seed["password"],
    )
    create = await api_client.post(
        "/api/v1/users",
        headers=_auth(token),
        json={
            "company_id": user_mgmt_seed["company_id"],
            "email": "x@usermgmt.co",
            "password": "Str0ng!Password",
            "first_name": "Nope",
            "last_name": "Nope",
            "role_name": "CUSTOMER",
        },
    )
    assert create.status_code == 403

    me = await api_client.get("/api/v1/users/me", headers=_auth(token))
    assert me.status_code == 200
    agent_id = me.json()["data"]["user_id"]

    # Agent may update own profile
    profile = await api_client.put(
        "/api/v1/users/me",
        headers=_auth(token),
        json={"display_name": "Alice A."},
    )
    assert profile.status_code == 200

    # Agent cannot list users
    listed = await api_client.get("/api/v1/users", headers=_auth(token))
    assert listed.status_code == 403

    _ = agent_id


@pytest.mark.asyncio
async def test_cross_tenant_user_access_denied(
    api_client: AsyncClient,
    user_mgmt_seed: dict,
) -> None:
    admin_token = await _token(
        api_client,
        user_mgmt_seed["emails"]["admin"],
        user_mgmt_seed["password"],
    )
    create = await api_client.post(
        "/api/v1/users",
        headers=_auth(admin_token),
        json={
            "company_id": user_mgmt_seed["company_id"],
            "email": "iso@usermgmt.co",
            "password": "Str0ng!Password",
            "first_name": "Iso",
            "last_name": "User",
            "role_name": "CUSTOMER",
        },
    )
    user_id = create.json()["data"]["user_id"]

    # Super admin can assign company
    super_token = await _token(
        api_client,
        user_mgmt_seed["emails"]["super"],
        user_mgmt_seed["password"],
    )
    moved = await api_client.patch(
        f"/api/v1/users/{user_id}/company",
        headers=_auth(super_token),
        json={"company_id": user_mgmt_seed["other_id"]},
    )
    assert moved.status_code == 200

    denied = await api_client.get(
        f"/api/v1/users/{user_id}",
        headers=_auth(admin_token),
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_password_change_requires_auth(
    api_client: AsyncClient,
    user_mgmt_seed: dict,
) -> None:
    resp = await api_client.patch(
        "/api/v1/users/1/change-password",
        json={"current_password": "x", "new_password": "Str0ng!Password2"},
    )
    assert resp.status_code == 401
