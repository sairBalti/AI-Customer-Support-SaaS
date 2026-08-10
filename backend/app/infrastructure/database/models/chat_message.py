"""Chat message SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class ChatMessageModel(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("message_uuid", name="uq_chat_messages_message_uuid"),
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_company_id", "company_id"),
        Index("ix_chat_messages_sender_id", "sender_id"),
        Index("ix_chat_messages_created_at", "created_at"),
        Index(
            "ix_chat_messages_company_id_session_id",
            "company_id",
            "session_id",
        ),
    )

    message_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey(
            "chat_sessions.session_id",
            name="fk_chat_messages_session_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_chat_messages_company_id"),
        nullable=False,
    )
    sender_id: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey("users.user_id", name="fk_chat_messages_sender_id"),
        nullable=True,
    )
    parent_message_id: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey("chat_messages.message_id", name="fk_chat_messages_parent_message_id"),
        nullable=True,
    )
    message_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="TEXT")
    sender_type: Mapped[str] = mapped_column(String(32), nullable=False, server_default="CUSTOMER")
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    formatted_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        server_default="0",
    )
    response_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    retrieved_chunks: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    citations: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    feedback: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
