"""Ticket SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
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


class TicketModel(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
        Index("ix_tickets_company_id", "company_id"),
        Index("ix_tickets_customer_id", "customer_id"),
        Index("ix_tickets_conversation_id", "conversation_id"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_assigned_to", "assigned_to"),
        Index("ix_tickets_priority", "priority"),
        Index(
            "ix_tickets_company_id_status",
            "company_id",
            "status",
        ),
    )

    ticket_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_tickets_company_id"),
        nullable=False,
    )
    customer_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("users.user_id", name="fk_tickets_customer_id"),
        nullable=False,
    )
    conversation_id: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey(
            "chat_sessions.session_id",
            name="fk_tickets_conversation_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    source_message_id: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey(
            "chat_messages.message_id",
            name="fk_tickets_source_message_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    assigned_to: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey(
            "users.user_id",
            name="fk_tickets_assigned_to",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    ticket_number: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, server_default="GENERAL")
    priority: Mapped[str] = mapped_column(String(32), nullable=False, server_default="MEDIUM")
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="OPEN")
    source: Mapped[str] = mapped_column(String(32), nullable=False, server_default="MANUAL")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
