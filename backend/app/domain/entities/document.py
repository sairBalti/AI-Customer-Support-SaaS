"""Document domain entity (metadata only — binaries live in object storage)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.enums.document_status import DocumentStatus, StorageProvider


@dataclass(slots=True)
class Document:
    """Tenant-scoped knowledge document metadata."""

    document_id: int
    company_id: int
    uploaded_by: int
    document_name: str
    original_filename: str
    storage_path: str
    storage_provider: StorageProvider
    mime_type: str
    file_extension: str
    file_size_bytes: int
    file_hash: str
    processing_status: DocumentStatus
    language: str
    version: int
    total_chunks: int
    created_at: datetime
    updated_at: datetime
    page_count: int | None = None
    embedding_provider: str | None = None
    embedding_model: str | None = None
    processing_started_at: datetime | None = None
    processing_completed_at: datetime | None = None
    indexed_at: datetime | None = None
    last_accessed_at: datetime | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    deleted_at: datetime | None = None
    failure_reason: str | None = None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    @property
    def is_ready(self) -> bool:
        return self.processing_status == DocumentStatus.COMPLETED and not self.is_deleted

    @property
    def is_failed(self) -> bool:
        return self.processing_status == DocumentStatus.FAILED
