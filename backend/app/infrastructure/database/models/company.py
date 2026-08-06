"""Company SQLAlchemy 2.0 ORM model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.company_status import CompanyStatus
from app.domain.enums.subscription_plan import SubscriptionPlan
from app.infrastructure.database.base import Base

# SQLite requires INTEGER PK for autoincrement; MySQL keeps BIGINT.
_CompanyId = BigInteger().with_variant(Integer(), "sqlite")


class CompanyModel(Base):
    """ORM mapping for the ``companies`` table."""

    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_status_subscription_plan", "status", "subscription_plan"),
        Index(
            "ix_companies_subscription_plan_created_at",
            "subscription_plan",
            "created_at",
        ),
        Index("ix_companies_deleted_at", "deleted_at"),
    )

    company_id: Mapped[int] = mapped_column(
        _CompanyId,
        primary_key=True,
        autoincrement=True,
    )
    company_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    company_slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, server_default="UTC")
    subscription_plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(
            SubscriptionPlan,
            name="subscription_plan",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        server_default=SubscriptionPlan.FREE.value,
    )
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, server_default="5")
    max_documents: Mapped[int] = mapped_column(Integer, nullable=False, server_default="50")
    max_storage_mb: Mapped[int] = mapped_column(Integer, nullable=False, server_default="500")
    monthly_ai_tokens: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default="100000",
    )
    token_usage: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(
            CompanyStatus,
            name="company_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        server_default=CompanyStatus.ACTIVE.value,
        index=True,
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
