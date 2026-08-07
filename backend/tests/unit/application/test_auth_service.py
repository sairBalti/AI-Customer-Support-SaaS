"""Unit tests for AuthService with in-memory doubles."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.services.auth.auth_service import AuthService
from app.core.security.password import hash_password
from app.domain.entities.refresh_token import RefreshToken
from app.domain.entities.user import AuthUser
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.auth import InvalidCredentialsError, RefreshTokenInvalidError
from app.domain.interfaces.repositories.auth_user_repository import AuthUserRepository
from app.domain.interfaces.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.interfaces.services.audit_logger import AuditLogger


class FakeUsers(AuthUserRepository):
    def __init__(self, user: AuthUser) -> None:
        self.user = user

    async def get_by_email(self, email: str) -> AuthUser | None:
        return self.user if self.user.email == email else None

    async def get_by_id(self, user_id: int) -> AuthUser | None:
        return self.user if self.user.user_id == user_id else None

    async def get_permissions_for_role(self, role_id: int) -> frozenset[str]:
        return self.user.permissions

    async def record_login_success(
        self, user_id: int, *, ip_address: str | None, at: datetime
    ) -> None:
        self.user.failed_login_attempts = 0
        self.user.last_login_at = at
        self.user.last_login_ip = ip_address

    async def record_login_failure(
        self,
        user_id: int,
        *,
        failed_login_attempts: int,
        locked_until: datetime | None,
    ) -> None:
        self.user.failed_login_attempts = failed_login_attempts
        self.user.locked_until = locked_until


class FakeRefresh(RefreshTokenRepository):
    def __init__(self) -> None:
        self.rows: dict[str, RefreshToken] = {}
        self._seq = 1

    async def create(self, data: dict[str, Any]) -> RefreshToken:
        token = RefreshToken(
            token_id=self._seq,
            user_id=data["user_id"],
            company_id=data["company_id"],
            token_hash=data["token_hash"],
            expires_at=data["expires_at"],
            created_at=datetime.now(UTC),
            user_agent=data.get("user_agent"),
            ip_address=data.get("ip_address"),
        )
        self._seq += 1
        self.rows[token.token_hash] = token
        return token

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.rows.get(token_hash)

    async def revoke(self, token_id: int, *, at: datetime) -> None:
        for token in self.rows.values():
            if token.token_id == token_id:
                token.revoked_at = at

    async def revoke_all_for_user(self, user_id: int, *, at: datetime) -> int:
        count = 0
        for token in self.rows.values():
            if token.user_id == user_id and token.revoked_at is None:
                token.revoked_at = at
                count += 1
        return count

    async def rotate(
        self, old_token_id: int, new_data: dict[str, Any], *, at: datetime
    ) -> RefreshToken:
        await self.revoke(old_token_id, at=at)
        return await self.create(new_data)


class FakeAudit(AuditLogger):
    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.events.append(kwargs)


def _user() -> AuthUser:
    now = datetime.now(UTC)
    return AuthUser(
        user_id=1,
        company_id=10,
        role_id=2,
        email="admin@acme.com",
        password_hash=hash_password("Str0ng!Password"),
        first_name="Ada",
        last_name="Lovelace",
        status=UserStatus.ACTIVE,
        is_email_verified=True,
        failed_login_attempts=0,
        created_at=now,
        updated_at=now,
        role_name="COMPANY_ADMIN",
        permissions=frozenset({"auth.login", "companies.read"}),
    )


@pytest.mark.asyncio
async def test_login_success_issues_tokens() -> None:
    users = FakeUsers(_user())
    refresh = FakeRefresh()
    audit = FakeAudit()
    service = AuthService(users, refresh, audit)
    session = await service.login(email="admin@acme.com", password="Str0ng!Password")
    await service.flush_audits()
    assert session.tokens.access_token
    assert session.tokens.refresh_token
    assert audit.events[-1]["action"] == "USER_LOGIN"


@pytest.mark.asyncio
async def test_login_invalid_password() -> None:
    service = AuthService(FakeUsers(_user()), FakeRefresh(), FakeAudit())
    with pytest.raises(InvalidCredentialsError):
        await service.login(email="admin@acme.com", password="wrong")


@pytest.mark.asyncio
async def test_refresh_rotates_token() -> None:
    users = FakeUsers(_user())
    refresh = FakeRefresh()
    service = AuthService(users, refresh, FakeAudit())
    first = await service.login(email="admin@acme.com", password="Str0ng!Password")
    second = await service.refresh(refresh_token=first.tokens.refresh_token)
    assert second.tokens.refresh_token != first.tokens.refresh_token
    with pytest.raises(RefreshTokenInvalidError):
        await service.refresh(refresh_token=first.tokens.refresh_token)
