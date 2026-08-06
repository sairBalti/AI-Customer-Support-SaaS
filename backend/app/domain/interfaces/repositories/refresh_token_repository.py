"""Refresh token repository port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.entities.refresh_token import RefreshToken


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def create(self, data: dict[str, Any]) -> RefreshToken:
        """Persist a hashed refresh token."""

    @abstractmethod
    async def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        """Lookup an active (non-revoked) refresh token by hash."""

    @abstractmethod
    async def revoke(self, token_id: int, *, at: datetime) -> None:
        """Revoke a single refresh token."""

    @abstractmethod
    async def revoke_all_for_user(self, user_id: int, *, at: datetime) -> int:
        """Revoke all active refresh tokens for a user. Returns count revoked."""

    @abstractmethod
    async def rotate(
        self,
        old_token_id: int,
        new_data: dict[str, Any],
        *,
        at: datetime,
    ) -> RefreshToken:
        """Revoke the old token and create a replacement (atomic)."""
