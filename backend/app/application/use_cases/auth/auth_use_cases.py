"""Auth use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth.auth_service import AuthService, AuthSession
from app.domain.entities.user import AuthUser
from app.domain.exceptions.auth import InvalidCredentialsError


class LoginUseCase:
    def __init__(self, session: AsyncSession, service: AuthService) -> None:
        self._session = session
        self._service = service

    async def execute(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        try:
            session = await self._service.login(
                email=email,
                password=password,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self._service.flush_audits()
            await self._session.commit()
        except InvalidCredentialsError:
            # Persist failed-attempt / lockout updates, then surface 401.
            await self._service.flush_audits()
            await self._session.commit()
            raise
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        return session


class RefreshTokenUseCase:
    def __init__(self, session: AsyncSession, service: AuthService) -> None:
        self._session = session
        self._service = service

    async def execute(
        self,
        *,
        refresh_token: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthSession:
        try:
            session = await self._service.refresh(
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self._service.flush_audits()
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        return session


class LogoutUseCase:
    def __init__(self, session: AsyncSession, service: AuthService) -> None:
        self._session = session
        self._service = service

    async def execute(
        self,
        *,
        refresh_token: str | None,
        user_id: int | None,
        revoke_all: bool = False,
    ) -> None:
        try:
            await self._service.logout(
                refresh_token=refresh_token,
                user_id=user_id,
                revoke_all=revoke_all,
            )
            await self._service.flush_audits()
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise


class GetCurrentUserUseCase:
    def __init__(self, service: AuthService) -> None:
        self._service = service

    async def execute(self, user_id: int) -> AuthUser:
        return await self._service.get_authenticated_user(user_id)
