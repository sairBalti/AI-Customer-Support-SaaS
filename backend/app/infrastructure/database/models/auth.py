"""SQLAlchemy ORM models for authentication tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.user_status import UserStatus
from app.infrastructure.database.base import Base

_BigIntPK = BigInteger().with_variant(Integer(), "sqlite")


class RoleModel(Base):
    """Roles table — shared by Authentication and Role Management (hybrid scoped).

    ``company_id IS NULL`` → global / platform role.
    ``company_id`` set → company-specific role.
    ``is_system_role`` → protected; only Super Admin may manage.
    """

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("company_id", "role_name", name="uq_roles_company_id_role_name"),
        Index("ix_roles_company_id", "company_id"),
        Index("ix_roles_is_system_role", "is_system_role"),
        Index("ix_roles_is_active", "is_active"),
        Index("ix_roles_deleted_at", "deleted_at"),
        Index("ix_roles_is_active_sort_order", "is_active", "sort_order"),
    )

    role_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int | None] = mapped_column(
        _BigIntPK,
        ForeignKey("companies.company_id", name="fk_roles_company_id_companies"),
        nullable=True,
    )
    role_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_system(self) -> bool:
        """Alias for ``is_system_role`` (hybrid-model wording)."""
        return bool(self.is_system_role)

    @property
    def is_global(self) -> bool:
        return self.company_id is None


class PermissionModel(Base):
    __tablename__ = "permissions"

    permission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    permission_name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    module: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_permission: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class RolePermissionModel(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )

    role_permission_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.role_id", name="fk_role_permissions_role_id_roles"),
        nullable=False,
        index=True,
    )
    permission_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("permissions.permission_id", name="fk_role_permissions_permission_id_permissions"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class UserModel(Base):
    """Users table — shared by Authentication and User Management modules."""

    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_company_id_status", "company_id", "status"),
        Index("ix_users_company_id_role_id", "company_id", "role_id"),
        Index("ix_users_company_id_email", "company_id", "email"),
        Index("ix_users_deleted_at", "deleted_at"),
        Index("ix_users_username", "username"),
    )

    user_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        _BigIntPK,
        ForeignKey("companies.company_id", name="fk_users_company_id_companies"),
        nullable=False,
        index=True,
    )
    role_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("roles.role_id", name="fk_users_role_id_roles"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, server_default="en")
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, server_default="UTC")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=32,
        ),
        nullable=False,
        server_default=UserStatus.ACTIVE.value,
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


class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("ix_refresh_tokens_user_id", "user_id"),
        Index("ix_refresh_tokens_expires_at", "expires_at"),
        Index("ix_refresh_tokens_token_hash", "token_hash", unique=True),
    )

    token_id: Mapped[int] = mapped_column(_BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        _BigIntPK,
        ForeignKey("users.user_id", name="fk_refresh_tokens_user_id_users", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[int] = mapped_column(
        _BigIntPK,
        ForeignKey("companies.company_id", name="fk_refresh_tokens_company_id_companies"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    replaced_by_token_id: Mapped[int | None] = mapped_column(_BigIntPK, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
