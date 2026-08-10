"""Audit log SQLAlchemy model — append-only."""

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
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")
_BigInt = BigInteger().with_variant(Integer(), "sqlite")


class AuditLogModel(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        UniqueConstraint("audit_uuid", name="uq_audit_logs_audit_uuid"),
        Index("ix_audit_logs_company_id", "company_id"),
        Index("ix_audit_logs_actor_user_id", "actor_user_id"),
        Index("ix_audit_logs_action", "action"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_entity_type_entity_id", "entity_type", "entity_id"),
        Index("ix_audit_logs_company_id_created_at", "company_id", "created_at"),
    )

    audit_log_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigInt,
        ForeignKey("companies.company_id", name="fk_audit_logs_company_id"),
        nullable=False,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        _BigInt,
        ForeignKey(
            "users.user_id",
            name="fk_audit_logs_actor_user_id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    audit_uuid: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(_BigInt, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
