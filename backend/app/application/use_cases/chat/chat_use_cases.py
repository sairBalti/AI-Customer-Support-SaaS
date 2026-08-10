"""Chat application use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.chat import (
    ChatAnswerResult,
    CreateConversationInput,
    SendChatMessageInput,
)
from app.application.services.chat.chat_service import ChatService
from app.domain.entities.chat_message import ChatMessage
from app.domain.entities.chat_session import ChatSession


class CreateConversationUseCase:
    def __init__(self, session: AsyncSession, service: ChatService) -> None:
        self._db = session
        self._chat = service

    async def execute(
        self,
        data: CreateConversationInput,
        actor: RequestActor,
    ) -> ChatSession:
        try:
            result = await self._chat.create_conversation(data, actor)
            await self._db.commit()
            await self._chat.flush_audits()
            return result
        except Exception:
            self._chat.discard_audits()
            await self._db.rollback()
            raise


class ListConversationsUseCase:
    def __init__(self, session: AsyncSession, service: ChatService) -> None:
        self._db = session
        self._chat = service

    async def execute(
        self,
        actor: RequestActor,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        return await self._chat.list_conversations(actor, limit=limit, offset=offset)


class GetConversationUseCase:
    def __init__(self, session: AsyncSession, service: ChatService) -> None:
        self._db = session
        self._chat = service

    async def execute(
        self,
        conversation_id: int,
        actor: RequestActor,
    ) -> tuple[ChatSession, list[ChatMessage]]:
        return await self._chat.get_conversation(conversation_id, actor)


class SendChatMessageUseCase:
    def __init__(self, session: AsyncSession, service: ChatService) -> None:
        self._db = session
        self._chat = service

    async def execute(
        self,
        conversation_id: int,
        data: SendChatMessageInput,
        actor: RequestActor,
    ) -> ChatAnswerResult:
        try:
            result = await self._chat.send_message(conversation_id, data, actor)
            await self._db.commit()
            await self._chat.flush_audits()
            return result
        except Exception:
            self._chat.discard_audits()
            await self._db.rollback()
            raise
