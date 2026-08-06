"""Integration tests for authentication endpoints."""

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
async def auth_seed(db_session: AsyncSession) -> dict:
    company = CompanyModel(
        company_name="Auth Co",
        company_slug="auth-co",
        email="ops@auth.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        status=CompanyStatus.ACTIVE,
        max_users=5,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100000,
        token_usage=0,
    )
    db_session.add(company)
    await db_session.flush()
    roles = await seed_rbac(db_session)
    user = UserModel(
        company_id=company.company_id,
        role_id=roles["COMPANY_ADMIN"],
        first_name="Ada",
        last_name="Lovelace",
        email="ada@auth.co",
        password_hash=hash_password("Str0ng!Password"),
        status=UserStatus.ACTIVE,
        is_email_verified=True,
    )
    db_session.add(user)
    await db_session.commit()
    return {"email": "ada@auth.co", "password": "Str0ng!Password", "company_id": company.company_id}


@pytest.mark.asyncio
async def test_login_refresh_me_logout_flow(api_client: AsyncClient, auth_seed: dict) -> None:
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": auth_seed["email"], "password": auth_seed["password"]},
    )
    assert login.status_code == 200, login.text
    payload = login.json()["data"]
    access = payload["tokens"]["access_token"]
    refresh = payload["tokens"]["refresh_token"]
    assert payload["user"]["email"] == auth_seed["email"]
    assert "companies.read" in payload["user"]["permissions"] or payload["user"]["role_name"]

    me = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["company_id"] == auth_seed["company_id"]

    rotated = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert rotated.status_code == 200
    new_refresh = rotated.json()["data"]["tokens"]["refresh_token"]
    assert new_refresh != refresh

    # Old refresh token must be rejected after rotation.
    reuse = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert reuse.status_code == 401

    logout = await api_client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": new_refresh},
        headers={"Authorization": f"Bearer {rotated.json()['data']['tokens']['access_token']}"},
    )
    assert logout.status_code == 200


@pytest.mark.asyncio
async def test_login_rejects_bad_password(api_client: AsyncClient, auth_seed: dict) -> None:
    resp = await api_client.post(
        "/api/v1/auth/login",
        json={"email": auth_seed["email"], "password": "nope"},
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_requires_bearer(api_client: AsyncClient) -> None:
    resp = await api_client.get("/api/v1/auth/me")
    assert resp.status_code == 401
