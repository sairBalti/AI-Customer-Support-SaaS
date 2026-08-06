"""Authentication application service."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from app.application.context import RequestActor
from app.core.config import get_settings
from app.core.security.jwt import create_access_token
from app.core.security.password import verify_password
from app.domain.entities.user import AuthUser
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.user_status import UserStatus
from app.domain.exceptions.auth import (
    AccountInactiveError,
    AccountLockedError,
    InvalidCredentialsError,
    RefreshTokenInvalidError,
    TokenInvalidError,
)
from app.domain.interfaces.repositories.auth_user_repository import AuthUserRepository
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.refresh_token_repository import RefreshTokenRepository
from app.domain.interfaces.services.audit_logger import AuditLogger

MAX_FAILED_ATTEMPTS = 5
LOCK_MINUTES = 30
_ACTIVE_COMPANY_STATUSES = frozenset({CompanyStatus.ACTIVE, CompanyStatus.TRIAL})


@dataclass(slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 0


@dataclass(slots=True)
class AuthSession:
    tokens: TokenPair
    user: AuthUser


class AuthService:
    """Login, refresh, logout, and token validation rules."""

    def __init__(
        self,
        users: AuthUserRepository,
        refresh_tokens: RefreshTokenRepository,
        audit_logger: AuditLogger,
        companies: CompanyRepository | None = None,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._companies = companies
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        events = list(self._pending_audits)
        self._pending_audits.clear()
        for event in events:
            await self._audit.log(**event)

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        normalized = email.strip().lower()
        user = await self._users.get_by_email(normalized)
        if user is None:
            raise InvalidCredentialsError()

        self._assert_can_authenticate(user)

        if not verify_password(password, user.password_hash):
            await self._handle_failed_login(user)
            raise InvalidCredentialsError()

        await self._assert_company_allows_auth(user)

        now = datetime.now(UTC)
        await self._users.record_login_success(user.user_id, ip_address=ip_address, at=now)
        tokens = await self._issue_session(
            user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._queue_audit(
            action="USER_LOGIN",
            user_id=user.user_id,
            company_id=user.company_id,
            metadata={"email": user.email},
        )
        # Reload permissions/status snapshot after successful login bookkeeping.
        refreshed = await self._users.get_by_id(user.user_id)
        return AuthSession(tokens=tokens, user=refreshed or user)

    async def refresh(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        token_hash = self.hash_refresh_token(refresh_token)
        stored = await self._refresh_tokens.get_by_hash(token_hash)
        if stored is None or stored.is_revoked:
            raise RefreshTokenInvalidError()

        now = datetime.now(UTC)
        expires = stored.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires <= now:
            await self._refresh_tokens.revoke(stored.token_id, at=now)
            raise RefreshTokenInvalidError("Refresh token has expired.")

        user = await self._users.get_by_id(stored.user_id)
        if user is None:
            raise RefreshTokenInvalidError()
        self._assert_can_authenticate(user)
        await self._assert_company_allows_auth(user)

        settings = get_settings()
        raw_new = secrets.token_urlsafe(48)
        new_hash = self.hash_refresh_token(raw_new)
        new_entity = await self._refresh_tokens.rotate(
            stored.token_id,
            {
                "user_id": user.user_id,
                "company_id": user.company_id,
                "token_hash": new_hash,
                "expires_at": now + timedelta(days=settings.refresh_token_expire_days),
                "user_agent": user_agent,
                "ip_address": ip_address,
            },
            at=now,
        )
        access = create_access_token(
            user_id=user.user_id,
            company_id=user.company_id,
            role_name=user.role_name or "",
        )
        tokens = TokenPair(
            access_token=access,
            refresh_token=raw_new,
            expires_in=settings.access_token_expire_minutes * 60,
        )
        self._queue_audit(
            action="TOKEN_REFRESHED",
            user_id=user.user_id,
            company_id=user.company_id,
            metadata={"token_id": new_entity.token_id},
        )
        return AuthSession(tokens=tokens, user=user)

    async def logout(
        self,
        *,
        refresh_token: str | None,
        user_id: int | None,
        revoke_all: bool = False,
    ) -> None:
        now = datetime.now(UTC)
        if revoke_all and user_id is not None:
            await self._refresh_tokens.revoke_all_for_user(user_id, at=now)
        elif refresh_token:
            stored = await self._refresh_tokens.get_by_hash(self.hash_refresh_token(refresh_token))
            if stored is not None and not stored.is_revoked:
                await self._refresh_tokens.revoke(stored.token_id, at=now)
                user_id = stored.user_id
        self._queue_audit(
            action="USER_LOGOUT",
            user_id=user_id,
            company_id=None,
            metadata={"revoke_all": revoke_all},
        )

    async def get_authenticated_user(self, user_id: int) -> AuthUser:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise TokenInvalidError("User no longer exists.")
        self._assert_can_authenticate(user)
        await self._assert_company_allows_auth(user)
        return user

    def to_actor(self, user: AuthUser) -> RequestActor:
        return RequestActor(
            user_id=user.user_id,
            company_id=user.company_id,
            is_super_admin=user.is_super_admin,
            role_name=user.role_name,
            email=user.email,
            permissions=user.permissions,
        )

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    async def _issue_session(
        self,
        user: AuthUser,
        *,
        ip_address: str | None,
        user_agent: str | None,
    ) -> TokenPair:
        settings = get_settings()
        access = create_access_token(
            user_id=user.user_id,
            company_id=user.company_id,
            role_name=user.role_name or "",
        )
        raw_refresh = secrets.token_urlsafe(48)
        now = datetime.now(UTC)
        await self._refresh_tokens.create(
            {
                "user_id": user.user_id,
                "company_id": user.company_id,
                "token_hash": self.hash_refresh_token(raw_refresh),
                "expires_at": now + timedelta(days=settings.refresh_token_expire_days),
                "user_agent": user_agent,
                "ip_address": ip_address,
            }
        )
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.access_token_expire_minutes * 60,
        )

    def _assert_can_authenticate(self, user: AuthUser) -> None:
        if user.is_deleted:
            raise AccountInactiveError()
        now = datetime.now(UTC)
        if user.locked_until is not None:
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=UTC)
            if locked_until > now:
                raise AccountLockedError()
        if user.status in {UserStatus.SUSPENDED, UserStatus.INACTIVE}:
            raise AccountInactiveError()
        if user.status == UserStatus.LOCKED:
            # Lock window still enforced above; expired locks may proceed.
            if user.locked_until is None:
                raise AccountLockedError()
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=UTC)
            if locked_until > now:
                raise AccountLockedError()

    async def _assert_company_allows_auth(self, user: AuthUser) -> None:
        """Inactive/suspended/archived tenants cannot authenticate (except Super Admin)."""
        if user.is_super_admin or self._companies is None:
            return
        company = await self._companies.get_by_id(user.company_id)
        if company is None or company.status not in _ACTIVE_COMPANY_STATUSES:
            raise AccountInactiveError("Company is not allowed to sign in.")

    async def _handle_failed_login(self, user: AuthUser) -> None:
        attempts = user.failed_login_attempts + 1
        locked_until = None
        if attempts >= MAX_FAILED_ATTEMPTS:
            locked_until = datetime.now(UTC) + timedelta(minutes=LOCK_MINUTES)
        await self._users.record_login_failure(
            user.user_id,
            failed_login_attempts=attempts,
            locked_until=locked_until,
        )
        self._queue_audit(
            action="USER_LOGIN_FAILED",
            user_id=user.user_id,
            company_id=user.company_id,
            metadata={"attempts": attempts},
        )

    def _queue_audit(
        self,
        *,
        action: str,
        user_id: int | None,
        company_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._pending_audits.append(
            {
                "action": action,
                "entity": "users",
                "entity_id": user_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )
