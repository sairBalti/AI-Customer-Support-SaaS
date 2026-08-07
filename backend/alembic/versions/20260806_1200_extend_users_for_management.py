"""Alembic migration: user-management fields on existing users table.

Revision ID: 20260806_1200
Revises: 20260805_1000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_1200"
down_revision: str | None = "20260805_1000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=100), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "users",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_users_username"), "users", ["username"], unique=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_index(op.f("ix_users_username"), table_name="users")
    op.drop_column("users", "password_changed_at")
    op.drop_column("users", "must_change_password")
    op.drop_column("users", "username")
