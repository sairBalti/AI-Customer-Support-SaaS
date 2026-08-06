"""Audit logging port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AuditLogger(ABC):
    """Port for recording business audit events."""

    @abstractmethod
    async def log(
        self,
        *,
        action: str,
        entity: str,
        entity_id: int | str | None,
        company_id: int | None,
        user_id: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an immutable audit event (best-effort; must not break the request)."""
