"""Chat session repository port."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities.chat_session import ChatSession


class ChatSessionRepository(Protocol):
    async def create(self, data: dict[str, Any]) -> ChatSession: ...

    async def get_by_id(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
    ) -> ChatSession | None: ...

    async def list_by_company(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]: ...

    async def update(
        self,
        session_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> ChatSession | None: ...
