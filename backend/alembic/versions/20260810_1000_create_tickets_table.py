"""Alembic migration: tickets table + tickets.* permissions.

Revision ID: 20260810_1000
Revises: 20260809_1200
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260810_1000"
down_revision: str | None = "20260809_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("conversation_id", sa.BigInteger(), nullable=True),
        sa.Column("source_message_id", sa.BigInteger(), nullable=True),
        sa.Column("assigned_to", sa.BigInteger(), nullable=True),
        sa.Column("ticket_number", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), server_default="GENERAL", nullable=False),
        sa.Column("priority", sa.String(length=32), server_default="MEDIUM", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="OPEN", nullable=False),
        sa.Column("source", sa.String(length=32), server_default="MANUAL", nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.company_id"],
            name="fk_tickets_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.user_id"],
            name="fk_tickets_customer_id",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["chat_sessions.session_id"],
            name="fk_tickets_conversation_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["source_message_id"],
            ["chat_messages.message_id"],
            name="fk_tickets_source_message_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to"],
            ["users.user_id"],
            name="fk_tickets_assigned_to",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("ticket_id", name="pk_tickets"),
        sa.UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
    )
    op.create_index("ix_tickets_company_id", "tickets", ["company_id"])
    op.create_index("ix_tickets_customer_id", "tickets", ["customer_id"])
    op.create_index("ix_tickets_conversation_id", "tickets", ["conversation_id"])
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_assigned_to", "tickets", ["assigned_to"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_company_id_status", "tickets", ["company_id", "status"])

    _seed_ticket_permissions()


def _seed_ticket_permissions() -> None:
    conn = op.get_bind()
    needed = [
        ("tickets.create", "tickets", "create"),
        ("tickets.read", "tickets", "read"),
        ("tickets.update", "tickets", "update"),
        ("tickets.assign", "tickets", "assign"),
        ("tickets.resolve", "tickets", "resolve"),
        ("tickets.close", "tickets", "close"),
    ]
    existing = conn.execute(
        sa.text(
            "SELECT permission_name FROM permissions WHERE permission_name IN "
            "('tickets.create','tickets.read','tickets.update',"
            "'tickets.assign','tickets.resolve','tickets.close')"
        )
    ).fetchall()
    have = {row[0] for row in existing}
    permissions = sa.table(
        "permissions",
        sa.column("permission_name", sa.String),
        sa.column("module", sa.String),
        sa.column("action", sa.String),
        sa.column("is_system_permission", sa.Boolean),
        sa.column("is_active", sa.Boolean),
    )
    for name, module, action in needed:
        if name not in have:
            op.bulk_insert(
                permissions,
                [
                    {
                        "permission_name": name,
                        "module": module,
                        "action": action,
                        "is_system_permission": True,
                        "is_active": True,
                    }
                ],
            )

    role_rows = conn.execute(
        sa.text(
            "SELECT role_id, role_name FROM roles "
            "WHERE company_id IS NULL AND role_name IN "
            "('SUPER_ADMIN','COMPANY_ADMIN','SUPPORT_MANAGER','SUPPORT_AGENT','CUSTOMER')"
        )
    ).fetchall()
    role_map = {row[1]: row[0] for row in role_rows}
    perm_rows = conn.execute(
        sa.text(
            "SELECT permission_id, permission_name FROM permissions "
            "WHERE permission_name LIKE 'tickets.%'"
        )
    ).fetchall()
    rp = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )

    def _granted(role_id: int, permission_id: int) -> bool:
        row = conn.execute(
            sa.text(
                "SELECT 1 FROM role_permissions "
                "WHERE role_id = :rid AND permission_id = :pid LIMIT 1"
            ),
            {"rid": role_id, "pid": permission_id},
        ).first()
        return row is not None

    for permission_id, permission_name in perm_rows:
        for role_name, role_id in role_map.items():
            grant = False
            if role_name in {"SUPER_ADMIN", "COMPANY_ADMIN", "SUPPORT_MANAGER"}:
                grant = True
            elif role_name == "SUPPORT_AGENT":
                grant = permission_name in {
                    "tickets.create",
                    "tickets.read",
                    "tickets.update",
                    "tickets.resolve",
                }
            elif role_name == "CUSTOMER":
                grant = permission_name in {"tickets.create", "tickets.read"}
            if grant and not _granted(role_id, permission_id):
                op.bulk_insert(
                    rp,
                    [{"role_id": role_id, "permission_id": permission_id}],
                )


def downgrade() -> None:
    op.drop_index("ix_tickets_company_id_status", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_assigned_to", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_conversation_id", table_name="tickets")
    op.drop_index("ix_tickets_customer_id", table_name="tickets")
    op.drop_index("ix_tickets_company_id", table_name="tickets")
    op.drop_table("tickets")
