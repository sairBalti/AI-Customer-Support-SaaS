"""SQLAlchemy chat session repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.chat_session import ChatSession
from app.domain.interfaces.repositories.chat_session_repository import ChatSessionRepository
from app.infrastructure.database.mappers.chat_mapper import chat_session_to_entity
from app.infrastructure.database.models.chat_session import ChatSessionModel


class SQLAlchemyChatSessionRepository(ChatSessionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> ChatSession:
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        if "session_status" in payload and hasattr(payload["session_status"], "value"):
            payload["session_status"] = payload["session_status"].value
        model = ChatSessionModel(**payload)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return chat_session_to_entity(model)

    async def get_by_id(
        self,
        session_id: int,
        *,
        company_id: int | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
        if company_id is not None:
            stmt = stmt.where(ChatSessionModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return chat_session_to_entity(model) if model else None

    async def list_by_company(
        self,
        company_id: int,
        *,
        customer_id: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatSession]:
        stmt = (
            select(ChatSessionModel)
            .where(ChatSessionModel.company_id == company_id)
            .order_by(ChatSessionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if customer_id is not None:
            stmt = stmt.where(ChatSessionModel.customer_id == customer_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [chat_session_to_entity(r) for r in rows]

    async def update(
        self,
        session_id: int,
        data: dict[str, Any],
        *,
        company_id: int | None = None,
    ) -> ChatSession | None:
        stmt = select(ChatSessionModel).where(ChatSessionModel.session_id == session_id)
        if company_id is not None:
            stmt = stmt.where(ChatSessionModel.company_id == company_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        if model is None:
            return None
        payload = dict(data)
        if "metadata" in payload:
            payload["metadata_"] = payload.pop("metadata")
        if "session_status" in payload and hasattr(payload["session_status"], "value"):
            payload["session_status"] = payload["session_status"].value
        for key, value in payload.items():
            setattr(model, key, value)
        await self._session.flush()
        await self._session.refresh(model)
        return chat_session_to_entity(model)
