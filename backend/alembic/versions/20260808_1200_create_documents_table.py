"""Alembic migration: create documents table + seed documents.* permissions.

Revision ID: 20260808_1200
Revises: 20260806_1400
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_1200"
down_revision: str | None = "20260806_1400"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("document_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_by", sa.BigInteger(), nullable=False),
        sa.Column("document_name", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=1000), nullable=False),
        sa.Column(
            "storage_provider",
            sa.String(length=32),
            server_default="LOCAL",
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("file_extension", sa.String(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("file_hash", sa.String(length=96), nullable=False),
        sa.Column("language", sa.String(length=20), server_default="en", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("total_chunks", sa.Integer(), server_default="0", nullable=False),
        sa.Column("embedding_provider", sa.String(length=100), nullable=True),
        sa.Column("embedding_model", sa.String(length=100), nullable=True),
        sa.Column(
            "processing_status",
            sa.String(length=32),
            server_default="UPLOADED",
            nullable=False,
        ),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
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
            ["company_id"],
            ["companies.company_id"],
            name="fk_documents_company_id_companies",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.user_id"],
            name="fk_documents_uploaded_by_users",
        ),
        sa.PrimaryKeyConstraint("document_id", name="pk_documents"),
        sa.UniqueConstraint(
            "company_id",
            "file_hash",
            name="uq_documents_company_id_file_hash",
        ),
    )
    op.create_index("ix_documents_company_id", "documents", ["company_id"])
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"])
    op.create_index("ix_documents_processing_status", "documents", ["processing_status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])
    op.create_index("ix_documents_indexed_at", "documents", ["indexed_at"])
    op.create_index("ix_documents_language", "documents", ["language"])
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"])
    op.create_index(
        "ix_documents_company_id_processing_status",
        "documents",
        ["company_id", "processing_status"],
    )
    op.create_index(
        "ix_documents_company_id_created_at",
        "documents",
        ["company_id", "created_at"],
    )
    op.create_index(
        "ix_documents_company_id_document_name",
        "documents",
        ["company_id", "document_name"],
    )

    _seed_documents_permissions()


def _seed_documents_permissions() -> None:
    """Idempotently add documents.* permissions and grant to system roles."""
    conn = op.get_bind()
    needed = [
        ("documents.upload", "documents", "upload"),
        ("documents.read", "documents", "read"),
        ("documents.update", "documents", "update"),
        ("documents.delete", "documents", "delete"),
        ("documents.reindex", "documents", "reindex"),
    ]
    existing = conn.execute(
        sa.text(
            "SELECT permission_name FROM permissions WHERE permission_name IN "
            "('documents.upload','documents.read','documents.update',"
            "'documents.delete','documents.reindex')"
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
            "('SUPER_ADMIN','COMPANY_ADMIN','SUPPORT_MANAGER','SUPPORT_AGENT')"
        )
    ).fetchall()
    role_map = {row[1]: row[0] for row in role_rows}

    perm_rows = conn.execute(
        sa.text(
            "SELECT permission_id, permission_name FROM permissions "
            "WHERE permission_name LIKE 'documents.%'"
        )
    ).fetchall()

    rp = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer),
        sa.column("permission_id", sa.Integer),
    )

    def _already_granted(role_id: int, permission_id: int) -> bool:
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
            if role_name == "SUPER_ADMIN":
                grant = True
            elif role_name == "COMPANY_ADMIN":
                grant = True
            elif role_name == "SUPPORT_MANAGER":
                grant = permission_name in {
                    "documents.upload",
                    "documents.read",
                    "documents.update",
                    "documents.reindex",
                }
            elif role_name == "SUPPORT_AGENT":
                grant = permission_name == "documents.read"
            if grant and not _already_granted(role_id, permission_id):
                op.bulk_insert(
                    rp,
                    [{"role_id": role_id, "permission_id": permission_id}],
                )


def downgrade() -> None:
    op.drop_index("ix_documents_company_id_document_name", table_name="documents")
    op.drop_index("ix_documents_company_id_created_at", table_name="documents")
    op.drop_index("ix_documents_company_id_processing_status", table_name="documents")
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_index("ix_documents_language", table_name="documents")
    op.drop_index("ix_documents_indexed_at", table_name="documents")
    op.drop_index("ix_documents_created_at", table_name="documents")
    op.drop_index("ix_documents_processing_status", table_name="documents")
    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_index("ix_documents_company_id", table_name="documents")
    op.drop_table("documents")
