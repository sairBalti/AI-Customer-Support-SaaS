"""Alembic migration: chat_sessions + chat_messages + chat.* permissions.

Revision ID: 20260809_1200
Revises: 20260808_1600
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260809_1200"
down_revision: str | None = "20260808_1600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("session_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("customer_id", sa.BigInteger(), nullable=False),
        sa.Column("session_uuid", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=20), server_default="en", nullable=False),
        sa.Column("ai_provider", sa.String(length=100), server_default="fake", nullable=False),
        sa.Column("ai_model", sa.String(length=100), server_default="fake-v1", nullable=False),
        sa.Column(
            "session_status",
            sa.String(length=32),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("total_messages", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_prompt_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_completion_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "estimated_cost",
            sa.Numeric(12, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column("customer_satisfaction", sa.Integer(), nullable=True),
        sa.Column("escalation_required", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("escalated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ticket_id", sa.BigInteger(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_chat_sessions_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["users.user_id"],
            name="fk_chat_sessions_customer_id",
        ),
        sa.PrimaryKeyConstraint("session_id", name="pk_chat_sessions"),
        sa.UniqueConstraint("session_uuid", name="uq_chat_sessions_session_uuid"),
    )
    op.create_index("ix_chat_sessions_company_id", "chat_sessions", ["company_id"])
    op.create_index("ix_chat_sessions_customer_id", "chat_sessions", ["customer_id"])
    op.create_index("ix_chat_sessions_session_status", "chat_sessions", ["session_status"])
    op.create_index("ix_chat_sessions_last_message_at", "chat_sessions", ["last_message_at"])
    op.create_index(
        "ix_chat_sessions_company_id_customer_id",
        "chat_sessions",
        ["company_id", "customer_id"],
    )

    op.create_table(
        "chat_messages",
        sa.Column("message_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("sender_id", sa.BigInteger(), nullable=True),
        sa.Column("parent_message_id", sa.BigInteger(), nullable=True),
        sa.Column("message_uuid", sa.String(length=36), nullable=False),
        sa.Column("message_type", sa.String(length=32), server_default="TEXT", nullable=False),
        sa.Column("sender_type", sa.String(length=32), server_default="CUSTOMER", nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("formatted_message", sa.Text(), nullable=True),
        sa.Column("ai_model", sa.String(length=100), nullable=True),
        sa.Column("ai_provider", sa.String(length=100), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "estimated_cost",
            sa.Numeric(12, 6),
            server_default="0",
            nullable=False,
        ),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("retrieved_chunks", sa.JSON(), nullable=True),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.String(length=32), nullable=True),
        sa.Column("is_escalated", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_sessions.session_id"],
            name="fk_chat_messages_session_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.company_id"],
            name="fk_chat_messages_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["sender_id"],
            ["users.user_id"],
            name="fk_chat_messages_sender_id",
        ),
        sa.ForeignKeyConstraint(
            ["parent_message_id"],
            ["chat_messages.message_id"],
            name="fk_chat_messages_parent_message_id",
        ),
        sa.PrimaryKeyConstraint("message_id", name="pk_chat_messages"),
        sa.UniqueConstraint("message_uuid", name="uq_chat_messages_message_uuid"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_company_id", "chat_messages", ["company_id"])
    op.create_index("ix_chat_messages_sender_id", "chat_messages", ["sender_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])
    op.create_index(
        "ix_chat_messages_company_id_session_id",
        "chat_messages",
        ["company_id", "session_id"],
    )

    _seed_chat_permissions()


def _seed_chat_permissions() -> None:
    conn = op.get_bind()
    needed = [
        ("chat.start", "chat", "start"),
        ("chat.read", "chat", "read"),
    ]
    existing = conn.execute(
        sa.text(
            "SELECT permission_name FROM permissions WHERE permission_name IN "
            "('chat.start','chat.read')"
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
            "WHERE permission_name IN ('chat.start','chat.read')"
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
                grant = permission_name == "chat.read"
            elif role_name == "CUSTOMER":
                grant = True
            if grant and not _granted(role_id, permission_id):
                op.bulk_insert(
                    rp,
                    [{"role_id": role_id, "permission_id": permission_id}],
                )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_company_id_session_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_sender_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_company_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_company_id_customer_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_last_message_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_session_status", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_customer_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_company_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
