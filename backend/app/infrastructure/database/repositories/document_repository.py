"""SQLAlchemy Document repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus
from app.domain.interfaces.repositories.document_repository import DocumentRepository
from app.infrastructure.database.mappers.document_mapper import document_to_entity
from app.infrastructure.database.models.document import DocumentModel

_SORTABLE = {
    "created_at": DocumentModel.created_at,
    "updated_at": DocumentModel.updated_at,
    "document_name": DocumentModel.document_name,
    "file_size_bytes": DocumentModel.file_size_bytes,
    "processing_status": DocumentModel.processing_status,
    "original_filename": DocumentModel.original_filename,
}


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SQLAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: dict[str, Any]) -> Document:
        model = DocumentModel(**data)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return document_to_entity(model)

    async def get_by_id(
        self,
        document_id: int,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        stmt = select(DocumentModel).where(DocumentModel.document_id == document_id)
        if not include_deleted:
            stmt = stmt.where(DocumentModel.deleted_at.is_(None))
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return document_to_entity(model) if model else None

    async def get_by_hash(
        self,
        company_id: int,
        file_hash: str,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        stmt = select(DocumentModel).where(
            DocumentModel.company_id == company_id,
            DocumentModel.file_hash == file_hash,
        )
        if not include_deleted:
            stmt = stmt.where(DocumentModel.deleted_at.is_(None))
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return document_to_entity(model) if model else None

    async def update(
        self,
        document_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        existing = await self.get_by_id(document_id, include_deleted=include_deleted)
        if existing is None:
            return None
        await self._session.execute(
            update(DocumentModel).where(DocumentModel.document_id == document_id).values(**data)
        )
        await self._session.flush()
        return await self.get_by_id(
            document_id,
            include_deleted=True if "deleted_at" in data else include_deleted,
        )

    async def soft_delete(self, document_id: int, *, at: datetime) -> Document | None:
        existing = await self.get_by_id(document_id, include_deleted=False)
        if existing is None:
            return None
        # Free the unique (company_id, file_hash) slot for future re-uploads.
        released_hash = f"{existing.file_hash}:deleted:{existing.document_id}"
        return await self.update(
            document_id,
            {
                "deleted_at": at,
                "file_hash": released_hash,
                "processing_status": DocumentStatus.ARCHIVED,
            },
        )

    async def restore(self, document_id: int) -> Document | None:
        existing = await self.get_by_id(document_id, include_deleted=True)
        if existing is None or not existing.is_deleted:
            return existing
        original_hash = existing.file_hash
        marker = f":deleted:{existing.document_id}"
        if original_hash.endswith(marker):
            original_hash = original_hash[: -len(marker)]
        return await self.update(
            document_id,
            {
                "deleted_at": None,
                "file_hash": original_hash,
                "processing_status": DocumentStatus.QUEUED,
                "failure_reason": None,
            },
            include_deleted=True,
        )

    async def search(
        self,
        *,
        company_id: int | None,
        search: str | None,
        status: DocumentStatus | None,
        uploaded_by: int | None,
        page: int,
        page_size: int,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
    ) -> tuple[list[Document], int]:
        stmt = select(DocumentModel)
        count_stmt = select(func.count()).select_from(DocumentModel)

        if not include_deleted:
            stmt = stmt.where(DocumentModel.deleted_at.is_(None))
            count_stmt = count_stmt.where(DocumentModel.deleted_at.is_(None))
        if company_id is not None:
            stmt = stmt.where(DocumentModel.company_id == company_id)
            count_stmt = count_stmt.where(DocumentModel.company_id == company_id)
        if status is not None:
            stmt = stmt.where(DocumentModel.processing_status == status)
            count_stmt = count_stmt.where(DocumentModel.processing_status == status)
        if uploaded_by is not None:
            stmt = stmt.where(DocumentModel.uploaded_by == uploaded_by)
            count_stmt = count_stmt.where(DocumentModel.uploaded_by == uploaded_by)
        if search:
            pattern = f"%{_escape_like(search.strip())}%"
            filt = or_(
                DocumentModel.document_name.ilike(pattern, escape="\\"),
                DocumentModel.original_filename.ilike(pattern, escape="\\"),
                DocumentModel.description.ilike(pattern, escape="\\"),
            )
            stmt = stmt.where(filt)
            count_stmt = count_stmt.where(filt)

        total = int((await self._session.execute(count_stmt)).scalar_one())
        col = _SORTABLE.get(sort_by, DocumentModel.created_at)
        order = col.asc() if sort_order.lower() == "asc" else col.desc()
        stmt = stmt.order_by(order).offset((page - 1) * page_size).limit(page_size)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [document_to_entity(r) for r in rows], total

    async def count_by_company(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(DocumentModel)
            .where(DocumentModel.company_id == company_id)
        )
        if not include_deleted:
            stmt = stmt.where(DocumentModel.deleted_at.is_(None))
        return int((await self._session.execute(stmt)).scalar_one())

    async def sum_storage_bytes(
        self,
        company_id: int,
        *,
        include_deleted: bool = False,
    ) -> int:
        stmt = select(func.coalesce(func.sum(DocumentModel.file_size_bytes), 0)).where(
            DocumentModel.company_id == company_id
        )
        if not include_deleted:
            stmt = stmt.where(DocumentModel.deleted_at.is_(None))
        return int((await self._session.execute(stmt)).scalar_one())
