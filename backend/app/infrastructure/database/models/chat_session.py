"""Chat session SQLAlchemy model."""

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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class ChatSessionModel(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        UniqueConstraint("session_uuid", name="uq_chat_sessions_session_uuid"),
        Index("ix_chat_sessions_company_id", "company_id"),
        Index("ix_chat_sessions_customer_id", "customer_id"),
        Index("ix_chat_sessions_session_status", "session_status"),
        Index("ix_chat_sessions_last_message_at", "last_message_at"),
        Index(
            "ix_chat_sessions_company_id_customer_id",
            "company_id",
            "customer_id",
        ),
    )

    session_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_chat_sessions_company_id"),
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("users.user_id", name="fk_chat_sessions_customer_id"),
        nullable=False,
    )
    session_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="en")
    ai_provider: Mapped[str] = mapped_column(String(100), nullable=False, server_default="fake")
    ai_model: Mapped[str] = mapped_column(String(100), nullable=False, server_default="fake-v1")
    session_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="ACTIVE")
    total_messages: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_prompt_tokens: Mapped[int] = mapped_column(_BigInt, nullable=False, server_default="0")
    total_completion_tokens: Mapped[int] = mapped_column(
        _BigInt, nullable=False, server_default="0"
    )
    total_tokens: Mapped[int] = mapped_column(_BigInt, nullable=False, server_default="0")
    estimated_cost: Mapped[Decimal] = mapped_column(
        Numeric(12, 6),
        nullable=False,
        server_default="0",
    )
    customer_satisfaction: Mapped[int | None] = mapped_column(Integer, nullable=True)
    escalation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_id: Mapped[int | None] = mapped_column(_BigInt, nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
