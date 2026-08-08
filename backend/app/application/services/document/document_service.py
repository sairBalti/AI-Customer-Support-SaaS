"""Document management application service."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.application.context import RequestActor
from app.application.dto.document import (
    DocumentListQuery,
    StorageUsageResult,
    UpdateDocumentInput,
    UploadDocumentInput,
)
from app.application.services.document.document_rules import (
    extract_extension,
    normalize_document_name,
    sanitize_filename,
    validate_file_size,
    validate_mime_type,
    validate_sort_by,
)
from app.core.pagination import Page
from app.core.security.rbac import ensure_permissions
from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.domain.exceptions.document import (
    DocumentAccessDeniedError,
    DocumentConflictError,
    DocumentNotFoundError,
    DocumentOperationForbiddenError,
    DocumentValidationError,
)
from app.domain.interfaces.repositories.company_repository import CompanyRepository
from app.domain.interfaces.repositories.document_repository import DocumentRepository
from app.domain.interfaces.services.audit_logger import AuditLogger
from app.domain.interfaces.services.object_storage import ObjectStorage

_METADATA_FIELDS = frozenset({"document_name", "description", "language", "tags", "metadata"})


class DocumentService:
    """Metadata lifecycle: upload → validate → store → queue → delete/restore."""

    def __init__(
        self,
        documents: DocumentRepository,
        companies: CompanyRepository,
        storage: ObjectStorage,
        audit_logger: AuditLogger,
    ) -> None:
        self._documents = documents
        self._companies = companies
        self._storage = storage
        self._audit = audit_logger
        self._pending_audits: list[dict[str, Any]] = []

    async def flush_audits(self) -> None:
        events = list(self._pending_audits)
        self._pending_audits.clear()
        for event in events:
            await self._audit.log(**event)

    def discard_audits(self) -> None:
        self._pending_audits.clear()

    async def upload(self, data: UploadDocumentInput, actor: RequestActor) -> Document:
        ensure_permissions(actor, "documents.upload")
        company_id = self._resolve_company_id(data.company_id, actor)
        company = await self._companies.get_by_id(company_id)
        if company is None:
            raise DocumentValidationError("Company does not exist.")

        original = sanitize_filename(data.filename)
        extension = extract_extension(original)
        mime_type = validate_mime_type(data.content_type)
        validate_file_size(len(data.content), company.subscription_plan)

        file_hash = hashlib.sha256(data.content).hexdigest()
        duplicate = await self._documents.get_by_hash(company_id, file_hash)
        if duplicate is not None:
            raise DocumentConflictError(
                "An identical file already exists for this company.",
            )

        current_count = await self._documents.count_by_company(company_id)
        if current_count >= company.max_documents:
            raise DocumentValidationError("Company document quota exceeded.")

        used_bytes = await self._documents.sum_storage_bytes(company_id)
        max_bytes = company.max_storage_mb * 1024 * 1024
        if used_bytes + len(data.content) > max_bytes:
            raise DocumentValidationError("Company storage quota exceeded.")

        document_name = normalize_document_name(
            data.document_name or display_name_from_filename(original)
        )
        storage_key = f"companies/{company_id}/documents/{uuid.uuid4().hex}_{original}"
        stored_key = await self._storage.put(
            storage_key,
            data.content,
            content_type=mime_type,
        )

        now = datetime.now(UTC)
        try:
            provider = StorageProvider(self._storage.provider_name)
        except ValueError:
            provider = StorageProvider.LOCAL

        payload: dict[str, Any] = {
            "company_id": company_id,
            "uploaded_by": actor.user_id,
            "document_name": document_name,
            "original_filename": original,
            "storage_path": stored_key,
            "storage_provider": provider,
            "mime_type": mime_type,
            "file_extension": extension,
            "file_size_bytes": len(data.content),
            "file_hash": file_hash,
            "language": (data.language or "en").strip()[:20] or "en",
            "version": 1,
            "total_chunks": 0,
            "processing_status": DocumentStatus.QUEUED,
            "description": (data.description or "").strip() or None,
            "tags": list(data.tags or []),
            "doc_metadata": {},
            "created_at": now,
            "updated_at": now,
        }
        try:
            document = await self._documents.create(payload)
        except IntegrityError as exc:
            await self._storage.delete(stored_key)
            raise DocumentConflictError(
                "An identical file already exists for this company.",
            ) from exc

        self._queue_audit(
            action="document.upload",
            entity_id=document.document_id,
            company_id=company_id,
            user_id=actor.user_id,
            metadata={
                "filename": original,
                "file_size_bytes": document.file_size_bytes,
                "processing_status": document.processing_status.value,
            },
        )
        return document

    async def get_document(self, document_id: int, actor: RequestActor) -> Document:
        ensure_permissions(actor, "documents.read")
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        return document

    async def get_status(self, document_id: int, actor: RequestActor) -> Document:
        return await self.get_document(document_id, actor)

    async def list_documents(
        self,
        query: DocumentListQuery,
        actor: RequestActor,
    ) -> Page[Document]:
        ensure_permissions(actor, "documents.read")
        sort_by = validate_sort_by(query.sort_by)
        sort_order = "asc" if query.sort_order.lower() == "asc" else "desc"
        company_id = self._list_company_scope(query.company_id, actor)
        if query.include_deleted and not actor.is_super_admin:
            raise DocumentOperationForbiddenError(
                "Only Super Admin may list soft-deleted documents.",
            )

        items, total = await self._documents.search(
            company_id=company_id,
            search=query.search,
            status=query.status,
            uploaded_by=query.uploaded_by,
            page=query.page,
            page_size=query.page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=query.include_deleted,
        )
        return Page.of(
            items,
            page=query.page,
            page_size=query.page_size,
            total_items=total,
        )

    async def update_document(
        self,
        document_id: int,
        data: UpdateDocumentInput,
        actor: RequestActor,
    ) -> Document:
        ensure_permissions(actor, "documents.update")
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)

        values = {k: v for k, v in data.values.items() if k in _METADATA_FIELDS}
        if not values:
            raise DocumentValidationError("No updatable metadata fields provided.")

        payload: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if "document_name" in values:
            payload["document_name"] = normalize_document_name(str(values["document_name"]))
        if "description" in values:
            desc = values["description"]
            payload["description"] = (str(desc).strip() if desc is not None else None) or None
        if "language" in values:
            lang = str(values["language"] or "en").strip()[:20] or "en"
            payload["language"] = lang
        if "tags" in values:
            tags = values["tags"]
            if tags is None:
                payload["tags"] = []
            elif isinstance(tags, list):
                payload["tags"] = [str(t).strip() for t in tags if str(t).strip()]
            else:
                raise DocumentValidationError("tags must be a list of strings.")
        if "metadata" in values:
            meta = values["metadata"]
            if meta is None:
                payload["doc_metadata"] = {}
            elif isinstance(meta, dict):
                payload["doc_metadata"] = meta
            else:
                raise DocumentValidationError("metadata must be an object.")

        updated = await self._documents.update(document_id, payload)
        if updated is None:
            raise DocumentNotFoundError()
        self._queue_audit(
            action="document.update",
            entity_id=document_id,
            company_id=document.company_id,
            user_id=actor.user_id,
            metadata={"fields": sorted(payload.keys())},
        )
        return updated

    async def soft_delete(self, document_id: int, actor: RequestActor) -> Document:
        ensure_permissions(actor, "documents.delete")
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        deleted = await self._documents.soft_delete(document_id, at=datetime.now(UTC))
        if deleted is None:
            raise DocumentNotFoundError()
        self._queue_audit(
            action="document.delete",
            entity_id=document_id,
            company_id=document.company_id,
            user_id=actor.user_id,
        )
        return deleted

    async def restore(self, document_id: int, actor: RequestActor) -> Document:
        ensure_permissions(actor, "documents.delete")
        document = await self._documents.get_by_id(document_id, include_deleted=True)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        if not document.is_deleted:
            raise DocumentValidationError("Document is not deleted.")
        # Prevent unique hash collision with an active twin.
        marker = f":deleted:{document.document_id}"
        original_hash = document.file_hash
        if original_hash.endswith(marker):
            original_hash = original_hash[: -len(marker)]
        clash = await self._documents.get_by_hash(document.company_id, original_hash)
        if clash is not None:
            raise DocumentConflictError(
                "Cannot restore: an active document with the same file hash exists.",
            )
        restored = await self._documents.restore(document_id)
        if restored is None:
            raise DocumentNotFoundError()
        self._queue_audit(
            action="document.restore",
            entity_id=document_id,
            company_id=document.company_id,
            user_id=actor.user_id,
        )
        return restored

    async def queue_reindex(self, document_id: int, actor: RequestActor) -> Document:
        """Mark document QUEUED for a future AI/RAG pipeline (no workers yet)."""
        ensure_permissions(actor, "documents.reindex")
        document = await self._documents.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError()
        self._assert_tenant_access(document.company_id, actor)
        if document.processing_status == DocumentStatus.PROCESSING:
            raise DocumentOperationForbiddenError(
                "Document is already processing.",
            )
        updated = await self._documents.update(
            document_id,
            {
                "processing_status": DocumentStatus.QUEUED,
                "failure_reason": None,
                "processing_started_at": None,
                "processing_completed_at": None,
                "updated_at": datetime.now(UTC),
            },
        )
        if updated is None:
            raise DocumentNotFoundError()
        self._queue_audit(
            action="document.reindex",
            entity_id=document_id,
            company_id=document.company_id,
            user_id=actor.user_id,
        )
        return updated

    async def storage_usage(
        self,
        company_id: int | None,
        actor: RequestActor,
    ) -> StorageUsageResult:
        ensure_permissions(actor, "documents.read")
        resolved = self._resolve_company_id(company_id, actor)
        company = await self._companies.get_by_id(resolved)
        if company is None:
            raise DocumentValidationError("Company does not exist.")
        count = await self._documents.count_by_company(resolved)
        used = await self._documents.sum_storage_bytes(resolved)
        max_bytes = company.max_storage_mb * 1024 * 1024
        return StorageUsageResult(
            company_id=resolved,
            document_count=count,
            used_bytes=used,
            max_documents=company.max_documents,
            max_storage_bytes=max_bytes,
            remaining_documents=max(company.max_documents - count, 0),
            remaining_bytes=max(max_bytes - used, 0),
        )

    def _resolve_company_id(self, company_id: int | None, actor: RequestActor) -> int:
        if actor.is_super_admin:
            if company_id is None:
                if actor.company_id is None:
                    raise DocumentValidationError("company_id is required.")
                return int(actor.company_id)
            return int(company_id)
        if actor.company_id is None:
            raise DocumentAccessDeniedError("Authenticated user has no company.")
        if company_id is not None and int(company_id) != int(actor.company_id):
            raise DocumentAccessDeniedError(
                "Cannot access documents for another company.",
            )
        return int(actor.company_id)

    def _list_company_scope(
        self,
        company_id: int | None,
        actor: RequestActor,
    ) -> int | None:
        if actor.is_super_admin:
            return int(company_id) if company_id is not None else None
        if actor.company_id is None:
            raise DocumentAccessDeniedError("Authenticated user has no company.")
        if company_id is not None and int(company_id) != int(actor.company_id):
            raise DocumentAccessDeniedError(
                "Cannot access documents for another company.",
            )
        return int(actor.company_id)

    def _assert_tenant_access(self, company_id: int, actor: RequestActor) -> None:
        if actor.is_super_admin:
            return
        if actor.company_id is None or int(actor.company_id) != int(company_id):
            raise DocumentAccessDeniedError(
                "Cannot access documents for another company.",
            )

    def _queue_audit(
        self,
        *,
        action: str,
        entity_id: int,
        company_id: int | None,
        user_id: int | None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._pending_audits.append(
            {
                "action": action,
                "entity": "documents",
                "entity_id": entity_id,
                "company_id": company_id,
                "user_id": user_id,
                "metadata": metadata or {},
            }
        )


def display_name_from_filename(filename: str) -> str:
    """Derive a display name from a sanitized filename."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    return stem.replace("_", " ").strip() or filename
