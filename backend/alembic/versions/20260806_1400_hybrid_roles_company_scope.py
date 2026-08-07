"""Alembic migration: hybrid roles (nullable company_id + soft delete).

Revision ID: 20260806_1400
Revises: 20260806_1200

Extends existing ``roles`` table — does not recreate it.
- company_id NULL = global platform role
- company_id set = company-specific role
- uniqueness of role_name scoped per company_id
- soft delete via deleted_at
Existing ``is_system_role`` remains the system-role flag (is_system).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_1400"
down_revision: str | None = "20260806_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(op.f("uq_roles_role_name"), "roles", type_="unique")

    op.add_column("roles", sa.Column("company_id", sa.BigInteger(), nullable=True))
    op.add_column(
        "roles",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_roles_company_id_companies",
        "roles",
        "companies",
        ["company_id"],
        ["company_id"],
    )
    op.create_index(op.f("ix_roles_company_id"), "roles", ["company_id"], unique=False)
    op.create_index(op.f("ix_roles_is_system_role"), "roles", ["is_system_role"], unique=False)
    op.create_index(op.f("ix_roles_is_active"), "roles", ["is_active"], unique=False)
    op.create_index(op.f("ix_roles_deleted_at"), "roles", ["deleted_at"], unique=False)
    op.create_index(
        "ix_roles_is_active_sort_order",
        "roles",
        ["is_active", "sort_order"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_roles_company_id_role_name",
        "roles",
        ["company_id", "role_name"],
    )

    _seed_roles_permissions()


def _seed_roles_permissions() -> None:
    """Idempotently add roles.* permissions required by Role Management APIs."""
    conn = op.get_bind()
    existing = conn.execute(
        sa.text(
            "SELECT permission_name FROM permissions "
            "WHERE permission_name IN "
            "('roles.create','roles.read','roles.update','roles.delete')"
        )
    ).fetchall()
    have = {row[0] for row in existing}
    needed = [
        ("roles.create", "roles", "create"),
        ("roles.read", "roles", "read"),
        ("roles.update", "roles", "update"),
        ("roles.delete", "roles", "delete"),
    ]
    permissions = sa.table(
        "permissions",
        sa.column("permission_name", sa.String),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system_permission", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    to_insert = [
        {
            "permission_name": name,
            "module": module,
            "action": action,
            "description": name,
            "is_system_permission": True,
            "is_active": True,
        }
        for name, module, action in needed
        if name not in have
    ]
    if to_insert:
        op.bulk_insert(permissions, to_insert)

    # Grant to SUPER_ADMIN (all roles.*) and COMPANY_ADMIN (all roles.*).
    role_rows = conn.execute(
        sa.text(
            "SELECT role_id, role_name FROM roles "
            "WHERE role_name IN ('SUPER_ADMIN','COMPANY_ADMIN') "
            "AND company_id IS NULL AND deleted_at IS NULL"
        )
    ).fetchall()
    role_map = {name: int(rid) for rid, name in role_rows}
    perm_rows = conn.execute(
        sa.text(
            "SELECT permission_id, permission_name FROM permissions "
            "WHERE permission_name LIKE 'roles.%'"
        )
    ).fetchall()
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    mappings = []
    for perm_id, _name in perm_rows:
        for role_name in ("SUPER_ADMIN", "COMPANY_ADMIN"):
            rid = role_map.get(role_name)
            if rid is None:
                continue
            exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions "
                    "WHERE role_id = :rid AND permission_id = :pid"
                ),
                {"rid": rid, "pid": int(perm_id)},
            ).fetchone()
            if exists is None:
                mappings.append({"role_id": rid, "permission_id": int(perm_id)})
    if mappings:
        op.bulk_insert(role_permissions, mappings)


def downgrade() -> None:
    op.drop_constraint("uq_roles_company_id_role_name", "roles", type_="unique")
    op.drop_index("ix_roles_is_active_sort_order", table_name="roles")
    op.drop_index(op.f("ix_roles_deleted_at"), table_name="roles")
    op.drop_index(op.f("ix_roles_is_active"), table_name="roles")
    op.drop_index(op.f("ix_roles_is_system_role"), table_name="roles")
    op.drop_index(op.f("ix_roles_company_id"), table_name="roles")
    op.drop_constraint("fk_roles_company_id_companies", "roles", type_="foreignkey")
    op.drop_column("roles", "deleted_at")
    op.drop_column("roles", "company_id")
    op.create_unique_constraint(op.f("uq_roles_role_name"), "roles", ["role_name"])
