"""Integration tests for company API endpoints (authz + CRUD)."""

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
async def company_auth(db_session: AsyncSession) -> dict:
    """Seed RBAC + company + Super Admin / Company Admin / low-privilege users."""
    roles = await seed_rbac(db_session)

    platform = CompanyModel(
        company_name="Platform Co",
        company_slug="platform-co",
        email="root@platform.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.ENTERPRISE,
        status=CompanyStatus.ACTIVE,
        max_users=100,
        max_documents=1000,
        max_storage_mb=10000,
        monthly_ai_tokens=1_000_000,
        token_usage=0,
    )
    tenant = CompanyModel(
        company_name="Tenant Co",
        company_slug="tenant-co",
        email="ops@tenant.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=5,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    other = CompanyModel(
        company_name="Other Co",
        company_slug="other-co",
        email="ops@other.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=5,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
    )
    db_session.add_all([platform, tenant, other])
    await db_session.flush()

    password = "Str0ng!Password"
    hashed = hash_password(password)
    users = {
        "super": UserModel(
            company_id=platform.company_id,
            role_id=roles["SUPER_ADMIN"],
            first_name="Sue",
            last_name="Admin",
            email="super@platform.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "company_admin": UserModel(
            company_id=tenant.company_id,
            role_id=roles["COMPANY_ADMIN"],
            first_name="Cara",
            last_name="Admin",
            email="admin@tenant.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
        "customer": UserModel(
            company_id=tenant.company_id,
            role_id=roles["CUSTOMER"],
            first_name="Cust",
            last_name="Omer",
            email="user@tenant.co",
            password_hash=hashed,
            status=UserStatus.ACTIVE,
            is_email_verified=True,
        ),
    }
    db_session.add_all(users.values())
    await db_session.commit()
    return {
        "password": password,
        "tenant_id": int(tenant.company_id),
        "other_id": int(other.company_id),
        "emails": {
            "super": "super@platform.co",
            "company_admin": "admin@tenant.co",
            "customer": "user@tenant.co",
        },
    }


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_public_registration_without_token(
    api_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    await seed_rbac(db_session)
    await db_session.commit()

    create = await api_client.post(
        "/api/v1/companies",
        json={
            "company_name": "Acme Corporation",
            "email": "admin@acme.com",
            "timezone": "UTC",
            "phone": "+15551234567",
            "website": "https://acme.com",
            "admin_password": "Str0ng!Password",
            "admin_first_name": "Ada",
            "admin_last_name": "Admin",
        },
    )
    assert create.status_code == 201, create.text
    assert create.json()["data"]["company_slug"] == "acme-corporation"

    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@acme.com", "password": "Str0ng!Password"},
    )
    assert login.status_code == 200, login.text
    assert login.json()["data"]["user"]["role_name"] == "COMPANY_ADMIN"


@pytest.mark.asyncio
async def test_public_registration_requires_admin_password(api_client: AsyncClient) -> None:
    create = await api_client.post(
        "/api/v1/companies",
        json={
            "company_name": "No Password Co",
            "email": "ops@nopass.co",
            "timezone": "UTC",
        },
    )
    assert create.status_code == 422, create.text


@pytest.mark.asyncio
async def test_protected_endpoints_require_jwt(api_client: AsyncClient) -> None:
    listed = await api_client.get("/api/v1/companies")
    assert listed.status_code == 401

    fetched = await api_client.get("/api/v1/companies/1")
    assert fetched.status_code == 401

    updated = await api_client.put("/api/v1/companies/1", json={"industry": "Software"})
    assert updated.status_code == 401

    status_resp = await api_client.patch(
        "/api/v1/companies/1/status",
        json={"status": "ACTIVE"},
    )
    assert status_resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_flow_with_valid_token(
    api_client: AsyncClient,
    company_auth: dict,
) -> None:
    token = await _login(
        api_client,
        company_auth["emails"]["company_admin"],
        company_auth["password"],
    )
    company_id = company_auth["tenant_id"]

    listed = await api_client.get("/api/v1/companies", headers=_auth(token))
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] == 1

    fetched = await api_client.get(
        f"/api/v1/companies/{company_id}",
        headers=_auth(token),
    )
    assert fetched.status_code == 200

    updated = await api_client.put(
        f"/api/v1/companies/{company_id}",
        json={"industry": "Software", "country": "US"},
        headers=_auth(token),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["industry"] == "Software"


@pytest.mark.asyncio
async def test_admin_endpoints_forbidden_for_customer(
    api_client: AsyncClient,
    company_auth: dict,
) -> None:
    token = await _login(
        api_client,
        company_auth["emails"]["customer"],
        company_auth["password"],
    )
    company_id = company_auth["tenant_id"]

    denied_list = await api_client.get("/api/v1/companies", headers=_auth(token))
    assert denied_list.status_code == 403

    denied = await api_client.patch(
        f"/api/v1/companies/{company_id}/subscription",
        json={"subscription_plan": "PRO"},
        headers=_auth(token),
    )
    assert denied.status_code == 403

    deleted = await api_client.delete(
        f"/api/v1/companies/{company_id}",
        headers=_auth(token),
    )
    assert deleted.status_code == 403


@pytest.mark.asyncio
async def test_admin_endpoints_succeed_for_company_admin_and_super(
    api_client: AsyncClient,
    company_auth: dict,
) -> None:
    ca_token = await _login(
        api_client,
        company_auth["emails"]["company_admin"],
        company_auth["password"],
    )
    tenant_id = company_auth["tenant_id"]

    sub = await api_client.patch(
        f"/api/v1/companies/{tenant_id}/subscription",
        json={"subscription_plan": "PRO"},
        headers=_auth(ca_token),
    )
    assert sub.status_code == 200
    assert sub.json()["data"]["subscription_plan"] == "PRO"

    # Company Admin cannot manage another tenant.
    cross = await api_client.patch(
        f"/api/v1/companies/{company_auth['other_id']}/status",
        json={"status": "SUSPENDED"},
        headers=_auth(ca_token),
    )
    assert cross.status_code == 403

    super_token = await _login(
        api_client,
        company_auth["emails"]["super"],
        company_auth["password"],
    )
    status_resp = await api_client.patch(
        f"/api/v1/companies/{company_auth['other_id']}/status",
        json={"status": "SUSPENDED"},
        headers=_auth(super_token),
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["data"]["status"] == "SUSPENDED"

    deleted = await api_client.delete(
        f"/api/v1/companies/{company_auth['other_id']}",
        headers=_auth(super_token),
    )
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_cross_tenant_access_denied(
    api_client: AsyncClient,
    company_auth: dict,
) -> None:
    token = await _login(
        api_client,
        company_auth["emails"]["company_admin"],
        company_auth["password"],
    )
    denied = await api_client.get(
        f"/api/v1/companies/{company_auth['other_id']}",
        headers=_auth(token),
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_header_bypass_still_works_for_dev(
    api_client: AsyncClient,
) -> None:
    """AUTH_HEADER_BYPASS remains available for local scaffolding."""
    create = await api_client.post(
        "/api/v1/companies",
        json={"company_name": "Bypass Co", "email": "b@ypass.com"},
    )
    company_id = create.json()["data"]["company_id"]
    listed = await api_client.get(
        "/api/v1/companies",
        headers={"X-Super-Admin": "true"},
    )
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total_items"] >= 1

    resp = await api_client.get(
        "/api/v1/companies",
        params={"sort_by": "password"},
        headers={"X-Super-Admin": "true"},
    )
    assert resp.status_code == 422

    _ = company_id
