"""Unit tests for DocumentService rules and tenant isolation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from app.application.context import RequestActor
from app.application.dto.document import UpdateDocumentInput, UploadDocumentInput
from app.application.services.document.document_rules import (
    extract_extension,
    validate_file_size,
    validate_mime_type,
)
from app.application.services.document.document_service import DocumentService
from app.domain.entities.company import Company
from app.domain.entities.document import Document
from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.domain.exceptions.document import (
    DocumentAccessDeniedError,
    DocumentConflictError,
    DocumentNotFoundError,
    DocumentValidationError,
)


class _MemDocs:
    def __init__(self) -> None:
        self.items: dict[int, Document] = {}
        self._seq = 1

    async def create(self, data: dict[str, Any]) -> Document:
        doc_id = self._seq
        self._seq += 1
        now = datetime.now(UTC)
        doc = Document(
            document_id=doc_id,
            company_id=int(data["company_id"]),
            uploaded_by=int(data["uploaded_by"]),
            document_name=data["document_name"],
            original_filename=data["original_filename"],
            storage_path=data["storage_path"],
            storage_provider=data["storage_provider"],
            mime_type=data["mime_type"],
            file_extension=data["file_extension"],
            file_size_bytes=int(data["file_size_bytes"]),
            file_hash=data["file_hash"],
            processing_status=data["processing_status"],
            language=data.get("language", "en"),
            version=int(data.get("version", 1)),
            total_chunks=int(data.get("total_chunks", 0)),
            created_at=data.get("created_at", now),
            updated_at=data.get("updated_at", now),
            description=data.get("description"),
            tags=list(data.get("tags") or []),
            metadata=dict(data.get("doc_metadata") or {}),
        )
        self.items[doc_id] = doc
        return doc

    async def get_by_id(
        self, document_id: int, *, include_deleted: bool = False
    ) -> Document | None:
        doc = self.items.get(document_id)
        if doc is None:
            return None
        if not include_deleted and doc.is_deleted:
            return None
        return doc

    async def get_by_hash(
        self,
        company_id: int,
        file_hash: str,
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        for doc in self.items.values():
            if doc.company_id != company_id or doc.file_hash != file_hash:
                continue
            if not include_deleted and doc.is_deleted:
                continue
            return doc
        return None

    async def update(
        self,
        document_id: int,
        data: dict[str, Any],
        *,
        include_deleted: bool = False,
    ) -> Document | None:
        doc = await self.get_by_id(document_id, include_deleted=include_deleted)
        if doc is None:
            return None
        values = {
            "document_id": doc.document_id,
            "company_id": doc.company_id,
            "uploaded_by": doc.uploaded_by,
            "document_name": doc.document_name,
            "original_filename": doc.original_filename,
            "storage_path": doc.storage_path,
            "storage_provider": doc.storage_provider,
            "mime_type": doc.mime_type,
            "file_extension": doc.file_extension,
            "file_size_bytes": doc.file_size_bytes,
            "file_hash": doc.file_hash,
            "processing_status": doc.processing_status,
            "language": doc.language,
            "version": doc.version,
            "total_chunks": doc.total_chunks,
            "created_at": doc.created_at,
            "updated_at": doc.updated_at,
            "page_count": doc.page_count,
            "embedding_provider": doc.embedding_provider,
            "embedding_model": doc.embedding_model,
            "processing_started_at": doc.processing_started_at,
            "processing_completed_at": doc.processing_completed_at,
            "indexed_at": doc.indexed_at,
            "last_accessed_at": doc.last_accessed_at,
            "description": doc.description,
            "tags": list(doc.tags),
            "metadata": dict(doc.metadata),
            "deleted_at": doc.deleted_at,
            "failure_reason": doc.failure_reason,
        }
        values.update(data)
        if "doc_metadata" in data:
            values["metadata"] = data["doc_metadata"]
            values.pop("doc_metadata", None)
        updated = Document(**values)
        self.items[document_id] = updated
        return updated

    async def soft_delete(self, document_id: int, *, at: datetime) -> Document | None:
        doc = await self.get_by_id(document_id)
        if doc is None:
            return None
        return await self.update(
            document_id,
            {
                "deleted_at": at,
                "file_hash": f"{doc.file_hash}:deleted:{doc.document_id}",
                "processing_status": DocumentStatus.ARCHIVED,
            },
        )

    async def restore(self, document_id: int) -> Document | None:
        doc = await self.get_by_id(document_id, include_deleted=True)
        if doc is None:
            return None
        marker = f":deleted:{doc.document_id}"
        original = (
            doc.file_hash[: -len(marker)] if doc.file_hash.endswith(marker) else doc.file_hash
        )
        return await self.update(
            document_id,
            {
                "deleted_at": None,
                "file_hash": original,
                "processing_status": DocumentStatus.QUEUED,
                "failure_reason": None,
            },
            include_deleted=True,
        )

    async def search(self, **kwargs: Any) -> tuple[list[Document], int]:
        company_id = kwargs.get("company_id")
        include_deleted = kwargs.get("include_deleted", False)
        items = [
            d
            for d in self.items.values()
            if (company_id is None or d.company_id == company_id)
            and (include_deleted or not d.is_deleted)
        ]
        return items, len(items)

    async def count_by_company(self, company_id: int, *, include_deleted: bool = False) -> int:
        return len(
            [
                d
                for d in self.items.values()
                if d.company_id == company_id and (include_deleted or not d.is_deleted)
            ]
        )

    async def sum_storage_bytes(self, company_id: int, *, include_deleted: bool = False) -> int:
        return sum(
            d.file_size_bytes
            for d in self.items.values()
            if d.company_id == company_id and (include_deleted or not d.is_deleted)
        )


class _MemCompanies:
    def __init__(self, company: Company) -> None:
        self.company = company

    async def get_by_id(self, company_id: int, **_: Any) -> Company | None:
        if company_id == self.company.company_id:
            return self.company
        return None


class _MemStorage:
    provider_name = StorageProvider.LOCAL.value

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put(self, key: str, data: bytes, *, content_type: str | None = None) -> str:
        _ = content_type
        self.objects[key] = data
        return key

    async def get(self, key: str) -> bytes:
        return self.objects[key]

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.objects


class _NoopAudit:
    async def log(self, **kwargs: Any) -> None:
        _ = kwargs


def _company(company_id: int = 1) -> Company:
    now = datetime.now(UTC)
    return Company(
        company_id=company_id,
        company_name="Doc Co",
        company_slug="doc-co",
        email="ops@doc.co",
        timezone="UTC",
        subscription_plan=SubscriptionPlan.FREE,
        max_users=10,
        max_documents=50,
        max_storage_mb=500,
        monthly_ai_tokens=100_000,
        token_usage=0,
        status=CompanyStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def _service(company_id: int = 1) -> tuple[DocumentService, _MemDocs, _MemStorage]:
    docs = _MemDocs()
    storage = _MemStorage()
    service = DocumentService(
        documents=docs,
        companies=_MemCompanies(_company(company_id)),
        storage=storage,
        audit_logger=_NoopAudit(),
    )
    return service, docs, storage


def _admin(company_id: int = 1) -> RequestActor:
    return RequestActor(
        user_id=10,
        company_id=company_id,
        role_name="COMPANY_ADMIN",
        permissions=frozenset(
            {
                "documents.upload",
                "documents.read",
                "documents.update",
                "documents.delete",
                "documents.reindex",
            }
        ),
    )


@pytest.mark.asyncio
async def test_upload_stores_metadata_and_queues() -> None:
    service, docs, storage = _service()
    doc = await service.upload(
        UploadDocumentInput(
            company_id=None,
            document_name="Refund Policy",
            description="Policy",
            language="en",
            tags=["policy"],
            filename="refund.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.4 test",
        ),
        _admin(),
    )
    assert doc.processing_status == DocumentStatus.QUEUED
    assert doc.company_id == 1
    assert doc.file_size_bytes == len(b"%PDF-1.4 test")
    assert storage.objects[doc.storage_path] == b"%PDF-1.4 test"
    assert len(docs.items) == 1


@pytest.mark.asyncio
async def test_duplicate_hash_rejected() -> None:
    service, _, _ = _service()
    actor = _admin()
    payload = UploadDocumentInput(
        company_id=None,
        document_name="A",
        description=None,
        language="en",
        tags=[],
        filename="a.pdf",
        content_type="application/pdf",
        content=b"same-bytes",
    )
    await service.upload(payload, actor)
    with pytest.raises(DocumentConflictError):
        await service.upload(payload, actor)


@pytest.mark.asyncio
async def test_cross_tenant_access_denied() -> None:
    service, _, _ = _service(company_id=1)
    actor = _admin(company_id=1)
    doc = await service.upload(
        UploadDocumentInput(
            company_id=None,
            document_name="X",
            description=None,
            language="en",
            tags=[],
            filename="x.pdf",
            content_type="application/pdf",
            content=b"tenant-1",
        ),
        actor,
    )
    other = RequestActor(
        user_id=99,
        company_id=2,
        permissions=frozenset({"documents.read", "documents.delete"}),
    )
    with pytest.raises(DocumentAccessDeniedError):
        await service.get_document(doc.document_id, other)


@pytest.mark.asyncio
async def test_soft_delete_excludes_from_get_and_restore_works() -> None:
    service, _, _ = _service()
    actor = _admin()
    doc = await service.upload(
        UploadDocumentInput(
            company_id=None,
            document_name="Y",
            description=None,
            language="en",
            tags=[],
            filename="y.txt",
            content_type="text/plain",
            content=b"hello",
        ),
        actor,
    )
    deleted = await service.soft_delete(doc.document_id, actor)
    assert deleted.is_deleted
    with pytest.raises(DocumentNotFoundError):
        await service.get_document(doc.document_id, actor)
    restored = await service.restore(doc.document_id, actor)
    assert restored.deleted_at is None
    assert restored.processing_status == DocumentStatus.QUEUED


@pytest.mark.asyncio
async def test_update_metadata_only() -> None:
    service, _, _ = _service()
    actor = _admin()
    doc = await service.upload(
        UploadDocumentInput(
            company_id=None,
            document_name="Old",
            description=None,
            language="en",
            tags=[],
            filename="z.md",
            content_type="text/markdown",
            content=b"# hi",
        ),
        actor,
    )
    updated = await service.update_document(
        doc.document_id,
        UpdateDocumentInput(values={"document_name": "New", "tags": ["a", "b"]}),
        actor,
    )
    assert updated.document_name == "New"
    assert updated.tags == ["a", "b"]
    assert updated.storage_path == doc.storage_path


def test_validation_helpers() -> None:
    assert extract_extension("file.PDF") == ".pdf"
    assert validate_mime_type("application/pdf; charset=binary") == "application/pdf"
    with pytest.raises(DocumentValidationError):
        extract_extension("malware.exe")
    with pytest.raises(DocumentValidationError):
        validate_file_size(11 * 1024 * 1024, SubscriptionPlan.FREE)
