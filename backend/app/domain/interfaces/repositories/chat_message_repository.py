"""Chat message repository port."""

from __future__ import annotations

from typing import Any, Protocol

from app.domain.entities.chat_message import ChatMessage


class ChatMessageRepository(Protocol):
    async def create(self, data: dict[str, Any]) -> ChatMessage: ...

    async def list_by_session(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ChatMessage]: ...

    async def get_by_id(
        self,
        message_id: int,
        *,
        company_id: int | None = None,
    ) -> ChatMessage | None: ...
