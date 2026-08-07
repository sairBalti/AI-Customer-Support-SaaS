"""create auth tables (roles, permissions, users, refresh_tokens)

Revision ID: 20260805_1000
Revises: 20260804_1430
Create Date: 2026-08-05 10:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260805_1000"
down_revision: str | None = "20260804_1430"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("role_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("role_id", name=op.f("pk_roles")),
        sa.UniqueConstraint("role_name", name=op.f("uq_roles_role_name")),
    )

    op.create_table(
        "permissions",
        sa.Column("permission_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("permission_name", sa.String(length=150), nullable=False),
        sa.Column("module", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system_permission", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("permission_id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("permission_name", name=op.f("uq_permissions_permission_name")),
    )
    op.create_index(op.f("ix_permissions_module"), "permissions", ["module"], unique=False)

    op.create_table(
        "role_permissions",
        sa.Column("role_permission_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.permission_id"],
            name="fk_role_permissions_permission_id_permissions",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.role_id"], name="fk_role_permissions_role_id_roles"
        ),
        sa.PrimaryKeyConstraint("role_permission_id", name=op.f("pk_role_permissions")),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index(
        op.f("ix_role_permissions_role_id"), "role_permissions", ["role_id"], unique=False
    )
    op.create_index(
        op.f("ix_role_permissions_permission_id"),
        "role_permissions",
        ["permission_id"],
        unique=False,
    )

    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=50), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("job_title", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=20), server_default="en", nullable=False),
        sa.Column("timezone", sa.String(length=100), server_default="UTC", nullable=False),
        sa.Column("is_email_verified", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(length=45), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="ACTIVE", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.company_id"], name="fk_users_company_id_companies"
        ),
        sa.ForeignKeyConstraint(["role_id"], ["roles.role_id"], name="fk_users_role_id_roles"),
        sa.PrimaryKeyConstraint("user_id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )
    op.create_index(op.f("ix_users_company_id"), "users", ["company_id"], unique=False)
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"], unique=False)
    op.create_index("ix_users_company_id_status", "users", ["company_id", "status"], unique=False)
    op.create_index("ix_users_company_id_role_id", "users", ["company_id", "role_id"], unique=False)
    op.create_index("ix_users_company_id_email", "users", ["company_id", "email"], unique=False)

    op.create_table(
        "refresh_tokens",
        sa.Column("token_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_token_id", sa.BigInteger(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.company_id"], name="fk_refresh_tokens_company_id_companies"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("token_id", name=op.f("pk_refresh_tokens")),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)
    op.create_index("ix_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"], unique=False)
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    _seed_rbac()


def _seed_rbac() -> None:
    roles = sa.table(
        "roles",
        sa.column("role_id", sa.Integer),
        sa.column("role_name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system_role", sa.Boolean),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    permissions = sa.table(
        "permissions",
        sa.column("permission_id", sa.Integer),
        sa.column("permission_name", sa.String),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system_permission", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )

    role_rows = [
        {
            "role_id": 1,
            "role_name": "SUPER_ADMIN",
            "display_name": "Super Admin",
            "description": "Platform administrator",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 1,
        },
        {
            "role_id": 2,
            "role_name": "COMPANY_ADMIN",
            "display_name": "Company Admin",
            "description": "Company owner/administrator",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 2,
        },
        {
            "role_id": 3,
            "role_name": "SUPPORT_MANAGER",
            "display_name": "Support Manager",
            "description": "Manages support agents",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 3,
        },
        {
            "role_id": 4,
            "role_name": "SUPPORT_AGENT",
            "display_name": "Support Agent",
            "description": "Handles customer tickets",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 4,
        },
        {
            "role_id": 5,
            "role_name": "CUSTOMER",
            "display_name": "Customer",
            "description": "End customer",
            "is_system_role": True,
            "is_active": True,
            "sort_order": 5,
        },
    ]
    perm_defs = [
        ("auth.login", "auth", "login"),
        ("auth.logout", "auth", "logout"),
        ("auth.refresh", "auth", "refresh"),
        ("companies.read", "companies", "read"),
        ("companies.update", "companies", "update"),
        ("companies.manage", "companies", "manage"),
        ("companies.archive", "companies", "archive"),
        ("users.create", "users", "create"),
        ("users.read", "users", "read"),
        ("users.update", "users", "update"),
        ("users.delete", "users", "delete"),
    ]
    perm_rows = [
        {
            "permission_id": idx,
            "permission_name": name,
            "module": module,
            "action": action,
            "description": name,
            "is_system_permission": True,
            "is_active": True,
        }
        for idx, (name, module, action) in enumerate(perm_defs, start=1)
    ]
    op.bulk_insert(roles, role_rows)
    op.bulk_insert(permissions, perm_rows)

    # SUPER_ADMIN gets every permission; COMPANY_ADMIN gets company+auth; CUSTOMER gets auth only.
    mappings = []
    for perm_id in range(1, len(perm_rows) + 1):
        mappings.append({"role_id": 1, "permission_id": perm_id})
    for perm_id, (name, _, _) in enumerate(perm_defs, start=1):
        if name.startswith("auth.") or name.startswith("companies.") or name.startswith("users."):
            if name != "companies.archive":
                mappings.append({"role_id": 2, "permission_id": perm_id})
        if name.startswith("auth."):
            mappings.append({"role_id": 5, "permission_id": perm_id})
            mappings.append({"role_id": 4, "permission_id": perm_id})
            mappings.append({"role_id": 3, "permission_id": perm_id})
    # de-dupe
    unique = {(m["role_id"], m["permission_id"]): m for m in mappings}
    op.bulk_insert(role_permissions, list(unique.values()))


def downgrade() -> None:
    op.drop_table("refresh_tokens")
    op.drop_index("ix_users_company_id_email", table_name="users")
    op.drop_index("ix_users_company_id_role_id", table_name="users")
    op.drop_index("ix_users_company_id_status", table_name="users")
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_index(op.f("ix_users_company_id"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_role_permissions_permission_id"), table_name="role_permissions")
    op.drop_index(op.f("ix_role_permissions_role_id"), table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_permissions_module"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
