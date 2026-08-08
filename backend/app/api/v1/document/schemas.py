"""Document Management API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.entities.document import Document
from app.domain.enums.document_status import DocumentStatus, StorageProvider


class DocumentUpdateRequest(BaseModel):
    """Metadata-only update (file bytes are immutable)."""

    model_config = ConfigDict(extra="forbid")

    document_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    language: str | None = Field(default=None, min_length=2, max_length=20)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    language: str
    version: int
    page_count: int | None
    total_chunks: int
    embedding_provider: str | None
    embedding_model: str | None
    processing_status: DocumentStatus
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    indexed_at: datetime | None
    last_accessed_at: datetime | None
    description: str | None
    tags: list[str]
    metadata: dict[str, Any]
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_entity(cls, document: Document) -> DocumentResponse:
        return cls(
            document_id=document.document_id,
            company_id=document.company_id,
            uploaded_by=document.uploaded_by,
            document_name=document.document_name,
            original_filename=document.original_filename,
            storage_path=document.storage_path,
            storage_provider=document.storage_provider,
            mime_type=document.mime_type,
            file_extension=document.file_extension,
            file_size_bytes=document.file_size_bytes,
            file_hash=document.file_hash,
            language=document.language,
            version=document.version,
            page_count=document.page_count,
            total_chunks=document.total_chunks,
            embedding_provider=document.embedding_provider,
            embedding_model=document.embedding_model,
            processing_status=document.processing_status,
            processing_started_at=document.processing_started_at,
            processing_completed_at=document.processing_completed_at,
            indexed_at=document.indexed_at,
            last_accessed_at=document.last_accessed_at,
            description=document.description,
            tags=list(document.tags),
            metadata=dict(document.metadata),
            failure_reason=document.failure_reason,
            created_at=document.created_at,
            updated_at=document.updated_at,
            deleted_at=document.deleted_at,
        )


class DocumentStatusResponse(BaseModel):
    document_id: int
    processing_status: DocumentStatus
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    indexed_at: datetime | None
    total_chunks: int
    failure_reason: str | None
    is_ready: bool
    is_failed: bool


class StorageUsageResponse(BaseModel):
    company_id: int
    document_count: int
    used_bytes: int
    max_documents: int
    max_storage_bytes: int
    remaining_documents: int
    remaining_bytes: int

    @field_validator("used_bytes", "max_storage_bytes", "remaining_bytes", mode="before")
    @classmethod
    def _ints(cls, value: Any) -> int:
        return int(value)
