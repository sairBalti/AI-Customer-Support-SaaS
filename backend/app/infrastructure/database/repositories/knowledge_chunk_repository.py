"""SQLAlchemy knowledge chunk repository."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.knowledge_chunk import KnowledgeChunk
from app.domain.interfaces.repositories.knowledge_chunk_repository import (
    KnowledgeChunkRepository,
)
from app.infrastructure.database.mappers.knowledge_chunk_mapper import knowledge_chunk_to_entity
from app.infrastructure.database.models.knowledge_chunk import KnowledgeChunkModel


class SQLAlchemyKnowledgeChunkRepository(KnowledgeChunkRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def bulk_create(self, rows: list[dict[str, Any]]) -> list[KnowledgeChunk]:
        models = [KnowledgeChunkModel(**row) for row in rows]
        self._session.add_all(models)
        await self._session.flush()
        for model in models:
            await self._session.refresh(model)
        return [knowledge_chunk_to_entity(m) for m in models]

    async def list_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> list[KnowledgeChunk]:
        stmt = (
            select(KnowledgeChunkModel)
            .where(KnowledgeChunkModel.document_id == document_id)
            .order_by(KnowledgeChunkModel.chunk_number.asc())
        )
        if company_id is not None:
            stmt = stmt.where(KnowledgeChunkModel.company_id == company_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [knowledge_chunk_to_entity(r) for r in rows]

    async def get_by_uuid(self, chunk_uuid: str) -> KnowledgeChunk | None:
        stmt = select(KnowledgeChunkModel).where(KnowledgeChunkModel.chunk_uuid == chunk_uuid)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return knowledge_chunk_to_entity(model) if model else None

    async def delete_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> int:
        stmt = delete(KnowledgeChunkModel).where(KnowledgeChunkModel.document_id == document_id)
        if company_id is not None:
            stmt = stmt.where(KnowledgeChunkModel.company_id == company_id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return int(getattr(result, "rowcount", 0) or 0)

    async def count_by_document(
        self,
        document_id: int,
        *,
        company_id: int | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(KnowledgeChunkModel)
            .where(KnowledgeChunkModel.document_id == document_id)
        )
        if company_id is not None:
            stmt = stmt.where(KnowledgeChunkModel.company_id == company_id)
        return int((await self._session.execute(stmt)).scalar_one())
