"""Document management use cases."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.context import RequestActor
from app.application.dto.document import (
    DocumentListQuery,
    StorageUsageResult,
    UpdateDocumentInput,
    UploadDocumentInput,
)
from app.application.services.document.document_service import DocumentService
from app.core.pagination import Page
from app.domain.entities.document import Document


class _MutatingUseCase:
    def __init__(self, session: AsyncSession, service: DocumentService) -> None:
        self._session = session
        self._service = service

    async def _run(self, coro) -> Document:
        try:
            result = await coro
            await self._session.commit()
        except Exception:
            self._service.discard_audits()
            await self._session.rollback()
            raise
        await self._service.flush_audits()
        return result


class UploadDocumentUseCase(_MutatingUseCase):
    async def execute(self, data: UploadDocumentInput, actor: RequestActor) -> Document:
        return await self._run(self._service.upload(data, actor))


class UpdateDocumentUseCase(_MutatingUseCase):
    async def execute(
        self,
        document_id: int,
        data: UpdateDocumentInput,
        actor: RequestActor,
    ) -> Document:
        return await self._run(self._service.update_document(document_id, data, actor))


class SoftDeleteDocumentUseCase(_MutatingUseCase):
    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        return await self._run(self._service.soft_delete(document_id, actor))


class RestoreDocumentUseCase(_MutatingUseCase):
    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        return await self._run(self._service.restore(document_id, actor))


class ReindexDocumentUseCase(_MutatingUseCase):
    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        return await self._run(self._service.queue_reindex(document_id, actor))


class GetDocumentUseCase:
    def __init__(self, session: AsyncSession, service: DocumentService) -> None:
        self._service = service

    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        return await self._service.get_document(document_id, actor)


class GetDocumentStatusUseCase:
    def __init__(self, session: AsyncSession, service: DocumentService) -> None:
        self._service = service

    async def execute(self, document_id: int, actor: RequestActor) -> Document:
        return await self._service.get_status(document_id, actor)


class ListDocumentsUseCase:
    def __init__(self, session: AsyncSession, service: DocumentService) -> None:
        self._service = service

    async def execute(
        self,
        query: DocumentListQuery,
        actor: RequestActor,
    ) -> Page[Document]:
        return await self._service.list_documents(query, actor)


class StorageUsageUseCase:
    def __init__(self, session: AsyncSession, service: DocumentService) -> None:
        self._service = service

    async def execute(
        self,
        company_id: int | None,
        actor: RequestActor,
    ) -> StorageUsageResult:
        return await self._service.storage_usage(company_id, actor)
