"""Alembic migration: knowledge_chunks + knowledge.* permissions.

Revision ID: 20260808_1600
Revises: 20260808_1200
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260808_1600"
down_revision: str | None = "20260808_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_chunks",
        sa.Column("chunk_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("document_id", sa.BigInteger(), nullable=False),
        sa.Column("chunk_number", sa.Integer(), nullable=False),
        sa.Column("chunk_uuid", sa.String(length=36), nullable=False),
        sa.Column("embedding_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("character_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section_title", sa.String(length=255), nullable=True),
        sa.Column("overlap_previous", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("overlap_next", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("embedding_provider", sa.String(length=100), nullable=False),
        sa.Column("embedding_model", sa.String(length=100), nullable=False),
        sa.Column("embedding_dimension", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=20), server_default="en", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("retrieval_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("last_retrieved_at", sa.DateTime(timezone=True), nullable=True),
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
            name="fk_knowledge_chunks_company_id",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.document_id"],
            name="fk_knowledge_chunks_document_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("chunk_id", name="pk_knowledge_chunks"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_number",
            name="uq_knowledge_chunks_document_number",
        ),
        sa.UniqueConstraint("chunk_uuid", name="uq_knowledge_chunks_chunk_uuid"),
        sa.UniqueConstraint("embedding_id", name="uq_knowledge_chunks_embedding_id"),
    )
    op.create_index("ix_knowledge_chunks_company_id", "knowledge_chunks", ["company_id"])
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_chunk_number", "knowledge_chunks", ["chunk_number"])
    op.create_index("ix_knowledge_chunks_page_number", "knowledge_chunks", ["page_number"])
    op.create_index("ix_knowledge_chunks_embedding_id", "knowledge_chunks", ["embedding_id"])
    op.create_index("ix_knowledge_chunks_language", "knowledge_chunks", ["language"])
    op.create_index(
        "ix_knowledge_chunks_company_id_document_id",
        "knowledge_chunks",
        ["company_id", "document_id"],
    )

    _seed_knowledge_permissions()


def _seed_knowledge_permissions() -> None:
    conn = op.get_bind()
    needed = [
        ("knowledge.process", "knowledge", "process"),
        ("knowledge.search", "knowledge", "search"),
    ]
    existing = conn.execute(
        sa.text(
            "SELECT permission_name FROM permissions WHERE permission_name IN "
            "('knowledge.process','knowledge.search')"
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
            "WHERE permission_name LIKE 'knowledge.%'"
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
            if role_name in {"SUPER_ADMIN", "COMPANY_ADMIN"}:
                grant = True
            elif role_name == "SUPPORT_MANAGER":
                grant = True
            elif role_name == "SUPPORT_AGENT":
                grant = permission_name == "knowledge.search"
            if grant and not _granted(role_id, permission_id):
                op.bulk_insert(
                    rp,
                    [{"role_id": role_id, "permission_id": permission_id}],
                )


def downgrade() -> None:
    op.drop_index("ix_knowledge_chunks_company_id_document_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_language", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_embedding_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_page_number", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_chunk_number", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_document_id", table_name="knowledge_chunks")
    op.drop_index("ix_knowledge_chunks_company_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
