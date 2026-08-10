"""Alembic migration: audit_logs + audit.read permission.

Revision ID: 20260810_1400
Revises: 20260810_1000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_1400"
down_revision: str | None = "20260810_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("audit_log_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("actor_user_id", sa.BigInteger(), nullable=True),
        sa.Column("audit_uuid", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.company_id"],
            name="fk_audit_logs_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.user_id"],
            name="fk_audit_logs_actor_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("audit_log_id", name="pk_audit_logs"),
        sa.UniqueConstraint("audit_uuid", name="uq_audit_logs_audit_uuid"),
    )
    op.create_index("ix_audit_logs_company_id", "audit_logs", ["company_id"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_audit_logs_entity_type_entity_id",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_logs_company_id_created_at",
        "audit_logs",
        ["company_id", "created_at"],
    )

    _seed_audit_permissions()


def _seed_audit_permissions() -> None:
    conn = op.get_bind()
    existing = conn.execute(
        sa.text("SELECT permission_name FROM permissions WHERE permission_name = 'audit.read'")
    ).fetchall()
    if not existing:
        permissions = sa.table(
            "permissions",
            sa.column("permission_name", sa.String),
            sa.column("module", sa.String),
            sa.column("action", sa.String),
            sa.column("is_system_permission", sa.Boolean),
            sa.column("is_active", sa.Boolean),
        )
        op.bulk_insert(
            permissions,
            [
                {
                    "permission_name": "audit.read",
                    "module": "audit",
                    "action": "read",
                    "is_system_permission": True,
                    "is_active": True,
                }
            ],
        )

    role_rows = conn.execute(
        sa.text(
            "SELECT role_id, role_name FROM roles "
            "WHERE company_id IS NULL AND role_name IN "
            "('SUPER_ADMIN','COMPANY_ADMIN','SUPPORT_MANAGER')"
        )
    ).fetchall()
    role_map = {row[1]: row[0] for row in role_rows}
    perm_row = conn.execute(
        sa.text(
            "SELECT permission_id FROM permissions WHERE permission_name = 'audit.read' LIMIT 1"
        )
    ).first()
    if perm_row is None:
        return
    permission_id = perm_row[0]
    rp = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )
    for role_name, role_id in role_map.items():
        granted = conn.execute(
            sa.text(
                "SELECT 1 FROM role_permissions "
                "WHERE role_id = :rid AND permission_id = :pid LIMIT 1"
            ),
            {"rid": role_id, "pid": permission_id},
        ).first()
        if not granted:
            op.bulk_insert(
                rp,
                [{"role_id": role_id, "permission_id": permission_id}],
            )
            _ = role_name


def downgrade() -> None:
    conn = op.get_bind()
    perm_row = conn.execute(
        sa.text(
            "SELECT permission_id FROM permissions WHERE permission_name = 'audit.read' LIMIT 1"
        )
    ).first()
    if perm_row is not None:
        permission_id = perm_row[0]
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_id = :pid"),
            {"pid": permission_id},
        )
        conn.execute(
            sa.text("DELETE FROM permissions WHERE permission_id = :pid"),
            {"pid": permission_id},
        )

    op.drop_index("ix_audit_logs_company_id_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_type_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_company_id", table_name="audit_logs")
    op.drop_table("audit_logs")
