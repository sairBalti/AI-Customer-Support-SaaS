"""SQLAlchemy chat message repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chat_message import ChatMessage
from app.domain.interfaces.repositories.chat_message_repository import ChatMessageRepository
from app.infrastructure.database.mappers.chat_mapper import chat_message_to_entity
from app.infrastructure.database.models.chat_message import ChatMessageModel


class SQLAlchemyChatMessageRepository(ChatMessageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> ChatMessage:
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        for enum_key in ("message_type", "sender_type", "feedback"):
            if enum_key in payload and hasattr(payload[enum_key], "value"):
                payload[enum_key] = payload[enum_key].value
        model = ChatMessageModel(**payload)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return chat_message_to_entity(model)

    async def list_by_session(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at.asc(), ChatMessageModel.message_id.asc())
            .limit(limit)
            .offset(offset)
        )
        if company_id is not None:
            stmt = stmt.where(ChatMessageModel.company_id == company_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [chat_message_to_entity(r) for r in rows]

    async def get_by_id(
        self,
        message_id: int,
        *,
        company_id: int | None = None,
    ) -> ChatMessage | None:
        stmt = select(ChatMessageModel).where(ChatMessageModel.message_id == message_id)
        if company_id is not None:
            stmt = stmt.where(ChatMessageModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return chat_message_to_entity(model) if model else None
