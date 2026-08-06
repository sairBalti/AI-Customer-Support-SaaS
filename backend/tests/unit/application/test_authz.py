"""Unit tests for authentication and company authorization edges."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.application.context import RequestActor
from app.application.dto.company import CreateCompanyInput, UpdateSubscriptionInput
from app.application.services.auth.auth_service import AuthService
from app.application.services.company.company_service import CompanyService
from app.core.config import get_settings
from app.core.security.jwt import ALGORITHM, create_access_token, decode_access_token
from app.core.security.password import hash_password
from app.domain.entities.user import AuthUser
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.auth import (
    AccountInactiveError,
    InsufficientPermissionError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError,
)
from app.domain.exceptions.company import CompanyAccessDeniedError
from tests.unit.application.test_auth_service import FakeAudit, FakeRefresh, FakeUsers
from tests.unit.application.test_company_service import (
    InMemoryCompanyRepository,
    RecordingAuditLogger,
)


def _auth_user(**overrides: object) -> AuthUser:
    now = datetime.now(UTC)
    data = {
        "user_id": 1,
        "company_id": 10,
        "role_id": 2,
        "email": "admin@acme.com",
        "password_hash": hash_password("Str0ng!Password"),
        "first_name": "Ada",
        "last_name": "Lovelace",
        "status": UserStatus.ACTIVE,
        "is_email_verified": True,
        "failed_login_attempts": 0,
        "created_at": now,
        "updated_at": now,
        "role_name": "COMPANY_ADMIN",
        "permissions": frozenset({"auth.login", "companies.read", "companies.update", "companies.manage"}),
    }
    data.update(overrides)
    return AuthUser(**data)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_valid_login() -> None:
    service = AuthService(FakeUsers(_auth_user()), FakeRefresh(), FakeAudit())
    session = await service.login(email="admin@acme.com", password="Str0ng!Password")
    assert session.tokens.access_token
    payload = decode_access_token(session.tokens.access_token)
    assert payload["sub"] == "1"


@pytest.mark.asyncio
async def test_invalid_login() -> None:
    service = AuthService(FakeUsers(_auth_user()), FakeRefresh(), FakeAudit())
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="admin@acme.com", password="wrong")


def test_missing_jwt_raises_token_invalid_via_decode() -> None:
    with pytest.raises(TokenInvalidError):
        decode_access_token("")


def test_invalid_jwt() -> None:
    with pytest.raises(TokenInvalidError):
        decode_access_token("not.a.jwt.token")


def test_expired_jwt() -> None:
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "1",
            "company_id": 10,
            "role": "COMPANY_ADMIN",
            "type": "access",
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    with pytest.raises(TokenExpiredError):
        decode_access_token(token)


@pytest.mark.asyncio
async def test_user_without_required_permission() -> None:
    repo = InMemoryCompanyRepository()
    svc = CompanyService(repo, RecordingAuditLogger())
    admin = RequestActor(is_super_admin=True)
    company = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        admin,
    )
    actor = RequestActor(
        user_id=5,
        company_id=company.company_id,
        permissions=frozenset({"companies.read"}),
    )
    with pytest.raises(InsufficientPermissionError):
        await svc.update_subscription(
            company.company_id,
            UpdateSubscriptionInput(subscription_plan=SubscriptionPlan.PRO),
            actor,
        )


@pytest.mark.asyncio
async def test_admin_access_with_manage_permission() -> None:
    repo = InMemoryCompanyRepository()
    svc = CompanyService(repo, RecordingAuditLogger())
    admin = RequestActor(is_super_admin=True)
    company = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        admin,
    )
    actor = RequestActor(
        user_id=5,
        company_id=company.company_id,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"companies.manage"}),
    )
    updated = await svc.update_subscription(
        company.company_id,
        UpdateSubscriptionInput(subscription_plan=SubscriptionPlan.PRO),
        actor,
    )
    assert updated.subscription_plan == SubscriptionPlan.PRO


@pytest.mark.asyncio
async def test_cross_tenant_access_denial() -> None:
    repo = InMemoryCompanyRepository()
    svc = CompanyService(repo, RecordingAuditLogger())
    company = await svc.create_company(
        CreateCompanyInput(company_name="Acme Corporation", email="admin@acme.com"),
        RequestActor(is_super_admin=True),
    )
    actor = RequestActor(
        user_id=9,
        company_id=999,
        permissions=frozenset({"companies.read", "companies.manage"}),
    )
    with pytest.raises(CompanyAccessDeniedError):
        await svc.get_company(company.company_id, actor)


@pytest.mark.asyncio
async def test_soft_deleted_user_cannot_authenticate() -> None:
    user = _auth_user(deleted_at=datetime.now(UTC))
    service = AuthService(FakeUsers(user), FakeRefresh(), FakeAudit())
    with pytest.raises(AccountInactiveError):
        await service.get_authenticated_user(user.user_id)


@pytest.mark.asyncio
async def test_inactive_user_cannot_authenticate() -> None:
    user = _auth_user(status=UserStatus.INACTIVE)
    service = AuthService(FakeUsers(user), FakeRefresh(), FakeAudit())
    with pytest.raises(AccountInactiveError):
        await service.login(email="admin@acme.com", password="Str0ng!Password")


def test_create_access_token_helper() -> None:
    token = create_access_token(user_id=1, company_id=2, role_name="SUPER_ADMIN")
    assert decode_access_token(token)["role"] == "SUPER_ADMIN"
