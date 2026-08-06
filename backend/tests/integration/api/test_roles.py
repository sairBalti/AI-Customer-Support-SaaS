"""Integration tests for Role Management API (hybrid roles)."""

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
async def role_seed(db_session: AsyncSession) -> dict:
    roles = await seed_rbac(db_session)
    company = CompanyModel(
        company_name="Role Co",
        company_slug="role-co",
        email="ops@role.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add(company)
    await db_session.flush()
    password = "Str0ng!Password"
    hashed = hash_password(password)
    admin = UserModel(
        company_id=company.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Cara",
        last_name="Admin",
        email="admin@role.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    super_user = UserModel(
        company_id=company.company_id,
        role_id=roles["SUPER_ADMIN"],
        first_name="Sue",
        last_name="Root",
        email="super@role.co",
        password_hash=hashed,
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add_all([admin, super_user])
    await db_session.commit()
    return {
        "password": password,
        "company_id": int(company.company_id),
        "emails": {"admin": "admin@role.co", "super": "super@role.co"},
        "system_role_id": roles["COMPANY_ADMIN"],
    }


async def _token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_company_admin_role_crud(api_client: AsyncClient, role_seed: dict) -> None:
    token = await _token(api_client, role_seed["emails"]["admin"], role_seed["password"])
    create = await api_client.post(
        "/api/v1/roles",
        headers=_auth(token),
        json={
            "role_name": "billing_admin",
            "display_name": "Billing Admin",
            "description": "Manages billing",
        },
    )
    assert create.status_code == 201, create.text
    data = create.json()["data"]
    assert data["role_name"] == "BILLING_ADMIN"
    assert data["company_id"] == role_seed["company_id"]
    assert data["is_system_role"] is False
    role_id = data["role_id"]

    listed = await api_client.get("/api/v1/roles", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] >= 1

    updated = await api_client.put(
        f"/api/v1/roles/{role_id}",
        headers=_auth(token),
        json={"display_name": "Billing Administrator"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["display_name"] == "Billing Administrator"

    status_resp = await api_client.patch(
        f"/api/v1/roles/{role_id}/status",
        headers=_auth(token),
        json={"is_active": False},
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["is_active"] is False

    deleted = await api_client.delete(f"/api/v1/roles/{role_id}", headers=_auth(token))
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None

    restored = await api_client.patch(
        f"/api/v1/roles/{role_id}/restore",
        headers=_auth(token),
    )
    assert restored.status_code == 200
    assert restored.json()["data"]["deleted_at"] is None


@pytest.mark.asyncio
async def test_cannot_modify_or_delete_system_role(
    api_client: AsyncClient,
    role_seed: dict,
) -> None:
    token = await _token(api_client, role_seed["emails"]["admin"], role_seed["password"])
    denied = await api_client.put(
        f"/api/v1/roles/{role_seed['system_role_id']}",
        headers=_auth(token),
        json={"display_name": "Nope"},
    )
    assert denied.status_code == 403

    deleted = await api_client.delete(
        f"/api/v1/roles/{role_seed['system_role_id']}",
        headers=_auth(token),
    )
    assert deleted.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_creates_global_role(
    api_client: AsyncClient,
    role_seed: dict,
) -> None:
    token = await _token(api_client, role_seed["emails"]["super"], role_seed["password"])
    create = await api_client.post(
        "/api/v1/roles",
        headers=_auth(token),
        json={
            "role_name": "PLATFORM_SUPPORT",
            "display_name": "Platform Support",
            "is_system_role": True,
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["data"]["company_id"] is None
    assert create.json()["data"]["is_system"] is True


@pytest.mark.asyncio
async def test_patch_role_and_cross_tenant_denied(
    api_client: AsyncClient,
    role_seed: dict,
    db_session: AsyncSession,
) -> None:
    other = CompanyModel(
        company_name="Other Role Co",
        company_slug="other-role-co",
        email="ops@otherrole.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=25,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add(other)
    await db_session.flush()
    roles = await seed_rbac(db_session)
    outsider = UserModel(
        company_id=other.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Out",
        last_name="sider",
        email="admin@otherrole.co",
        password_hash=hash_password(role_seed["password"]),
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add(outsider)
    await db_session.commit()

    admin_token = await _token(
        api_client,
        role_seed["emails"]["admin"],
        role_seed["password"],
    )
    create = await api_client.post(
        "/api/v1/roles",
        headers=_auth(admin_token),
        json={"role_name": "desk_lead", "display_name": "Desk Lead"},
    )
    role_id = create.json()["data"]["role_id"]

    patched = await api_client.patch(
        f"/api/v1/roles/{role_id}",
        headers=_auth(admin_token),
        json={"description": "Front desk"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["description"] == "Front desk"

    other_token = await _token(api_client, "admin@otherrole.co", role_seed["password"])
    denied = await api_client.get(f"/api/v1/roles/{role_id}", headers=_auth(other_token))
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_roles_require_jwt(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/roles")
    assert resp.status_code == 401
