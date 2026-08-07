"""add companies.deleted_at index

Revision ID: 20260804_1430
Revises: 20260804_1200
Create Date: 2026-08-04 14:30:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260804_1430"
down_revision: str | None = "20260804_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_companies_deleted_at"),
        "companies",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_companies_deleted_at"), table_name="companies")
