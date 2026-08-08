"""Document SQLAlchemy 2.0 ORM model (metadata only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.domain.enums.document_status import DocumentStatus, StorageProvider
from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class DocumentModel(Base):
    """ORM mapping for the ``documents`` table."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("company_id", "file_hash", name="uq_documents_company_id_file_hash"),
        Index("ix_documents_company_id", "company_id"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_processing_status", "processing_status"),
        Index("ix_documents_created_at", "created_at"),
        Index("ix_documents_indexed_at", "indexed_at"),
        Index("ix_documents_language", "language"),
        Index("ix_documents_deleted_at", "deleted_at"),
        Index(
            "ix_documents_company_id_processing_status",
            "company_id",
            "processing_status",
        ),
        Index("ix_documents_company_id_created_at", "company_id", "created_at"),
        Index("ix_documents_company_id_document_name", "company_id", "document_name"),
    )

    document_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_documents_company_id_companies"),
        nullable=False,
    )
    uploaded_by: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("users.user_id", name="fk_documents_uploaded_by_users"),
        nullable=False,
    )
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_provider: Mapped[StorageProvider] = mapped_column(
        Enum(StorageProvider, name="storage_provider_enum", native_enum=False, length=32),
        nullable=False,
        server_default=StorageProvider.LOCAL.value,
    )
    mime_type: Mapped[str] = mapped_column(String(150), nullable=False)
    file_extension: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(_BigInt, nullable=False)
    file_hash: Mapped[str] = mapped_column(String(96), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="en")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    embedding_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    processing_status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum", native_enum=False, length=32),
        nullable=False,
        server_default=DocumentStatus.UPLOADED.value,
    )
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processing_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_accessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    doc_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
