"""Knowledge chunk SQLAlchemy 2.0 ORM model (metadata only)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
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

from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class KnowledgeChunkModel(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_number", name="uq_knowledge_chunks_document_number"),
        UniqueConstraint("chunk_uuid", name="uq_knowledge_chunks_chunk_uuid"),
        UniqueConstraint("embedding_id", name="uq_knowledge_chunks_embedding_id"),
        Index("ix_knowledge_chunks_company_id", "company_id"),
        Index("ix_knowledge_chunks_document_id", "document_id"),
        Index("ix_knowledge_chunks_chunk_number", "chunk_number"),
        Index("ix_knowledge_chunks_page_number", "page_number"),
        Index("ix_knowledge_chunks_embedding_id", "embedding_id"),
        Index("ix_knowledge_chunks_language", "language"),
        Index(
            "ix_knowledge_chunks_company_id_document_id",
            "company_id",
            "document_id",
        ),
    )

    chunk_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_knowledge_chunks_company_id"),
        nullable=False,
    )
    document_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey(
            "documents.document_id",
            name="fk_knowledge_chunks_document_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    chunk_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    embedding_id: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    character_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    overlap_previous: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    overlap_next: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    embedding_provider: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding_dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="en")
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="1")
    retrieval_count: Mapped[int] = mapped_column(_BigInt, nullable=False, server_default="0")
    last_retrieved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    chunk_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
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
