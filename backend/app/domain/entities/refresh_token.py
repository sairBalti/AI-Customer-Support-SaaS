"""Refresh token domain entity."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RefreshToken:
    token_id: int
    user_id: int
    company_id: int
    token_hash: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by_token_id: int | None = None
    user_agent: str | None = None
    ip_address: str | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
