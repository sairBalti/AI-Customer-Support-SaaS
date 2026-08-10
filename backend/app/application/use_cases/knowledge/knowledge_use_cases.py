"""Knowledge use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.knowledge import KnowledgeSearchInput
from app.application.services.document.document_service import DocumentService
from app.application.services.knowledge.knowledge_service import KnowledgeService
from app.domain.entities.document import Document
from app.domain.entities.knowledge_chunk import RetrievedChunk


class ProcessDocumentUseCase:
    def __init__(self, session: AsyncSession, knowledge: KnowledgeService) -> None:
        self._session = session
        self._knowledge = knowledge

    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        try:
            result = await self._knowledge.process_document(document_id, actor)
            await self._knowledge.flush_audits()
            await self._session.commit()
        except Exception:
            self._knowledge.discard_audits()
            await self._session.rollback()
            raise
        return result


class ReindexKnowledgeDocumentUseCase:
    def __init__(self, session: AsyncSession, knowledge: KnowledgeService) -> None:
        self._session = session
        self._knowledge = knowledge

    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        try:
            result = await self._knowledge.reindex_document(document_id, actor)
            await self._knowledge.flush_audits()
            await self._session.commit()
        except Exception:
            self._knowledge.discard_audits()
            await self._session.rollback()
            raise
        return result


class SearchKnowledgeUseCase:
    def __init__(self, session: AsyncSession, knowledge: KnowledgeService) -> None:
        self._session = session
        self._knowledge = knowledge

    async def execute(
        self,
        data: KnowledgeSearchInput,
        actor: RequestActor,
    ) -> list[RetrievedChunk]:
        try:
            result = await self._knowledge.search(data, actor)
            await self._knowledge.flush_audits()
            await self._session.commit()
        except Exception:
            self._knowledge.discard_audits()
            await self._session.rollback()
            raise
        return result


class SoftDeleteDocumentWithDeindexUseCase:
    """Soft-delete document metadata and remove indexed knowledge."""

    def __init__(
        self,
        session: AsyncSession,
        documents: DocumentService,
        knowledge: KnowledgeService,
    ) -> None:
        self._session = session
        self._documents = documents
        self._knowledge = knowledge

    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        try:
            deleted = await self._documents.soft_delete(document_id, actor)
            await self._knowledge.deindex_document(
                deleted.document_id,
                deleted.company_id,
                actor,
            )
            await self._documents.flush_audits()
            await self._knowledge.flush_audits()
            await self._session.commit()
        except Exception:
            self._documents.discard_audits()
            self._knowledge.discard_audits()
            await self._session.rollback()
            raise
        return deleted
