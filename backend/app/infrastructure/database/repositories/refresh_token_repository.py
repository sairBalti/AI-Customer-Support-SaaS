"""Refresh token repository adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.refresh_token import RefreshToken
from app.domain.interfaces.repositories.refresh_token_repository import RefreshTokenRepository
from app.infrastructure.database.mappers.auth_mapper import refresh_token_to_entity
from app.infrastructure.database.models.auth import RefreshTokenModel


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> RefreshToken:
        model = RefreshTokenModel(**data)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return refresh_token_to_entity(model)

    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        stmt = select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return refresh_token_to_entity(model) if model else None

    async def revoke(self, token_id: int, *, at: datetime) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_id == token_id)
            .where(RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )

    async def revoke_all_for_user(self, user_id: int, *, at: datetime) -> int:
        result = await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.user_id == user_id)
            .where(RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=at)
        )
        return int(getattr(result, "rowcount", 0) or 0)

    async def rotate(
        self,
        old_token_id: int,
        new_data: dict[str, Any],
        *,
        at: datetime,
    ) -> RefreshToken:
        new_token = await self.create(new_data)
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_id == old_token_id)
            .values(revoked_at=at, replaced_by_token_id=new_token.token_id)
        )
        return new_token
