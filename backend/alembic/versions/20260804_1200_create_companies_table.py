"""create companies table

Revision ID: 20260804_1200
Revises:
Create Date: 2026-08-04 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_1200"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("company_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=150), nullable=False),
        sa.Column("company_slug", sa.String(length=150), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("timezone", sa.String(length=100), server_default="UTC", nullable=False),
        sa.Column(
            "subscription_plan",
            sa.String(length=32),
            server_default="FREE",
            nullable=False,
        ),
        sa.Column("max_users", sa.Integer(), server_default="5", nullable=False),
        sa.Column("max_documents", sa.Integer(), server_default="50", nullable=False),
        sa.Column("max_storage_mb", sa.Integer(), server_default="500", nullable=False),
        sa.Column(
            "monthly_ai_tokens",
            sa.BigInteger(),
            server_default="100000",
            nullable=False,
        ),
        sa.Column("token_usage", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="ACTIVE",
            nullable=False,
        ),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("subscription_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("company_id", name=op.f("pk_companies")),
        sa.UniqueConstraint("company_name", name=op.f("uq_companies_company_name")),
        sa.UniqueConstraint("company_slug", name=op.f("uq_companies_company_slug")),
        sa.UniqueConstraint("email", name=op.f("uq_companies_email")),
    )
    op.create_index(op.f("ix_companies_status"), "companies", ["status"], unique=False)
    op.create_index(
        op.f("ix_companies_created_at"),
        "companies",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_subscription_expires_at"),
        "companies",
        ["subscription_expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_companies_last_activity_at"),
        "companies",
        ["last_activity_at"],
        unique=False,
    )
    op.create_index(
        "ix_companies_status_subscription_plan",
        "companies",
        ["status", "subscription_plan"],
        unique=False,
    )
    op.create_index(
        "ix_companies_subscription_plan_created_at",
        "companies",
        ["subscription_plan", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_companies_subscription_plan_created_at", table_name="companies")
    op.drop_index("ix_companies_status_subscription_plan", table_name="companies")
    op.drop_index(op.f("ix_companies_last_activity_at"), table_name="companies")
    op.drop_index(op.f("ix_companies_subscription_expires_at"), table_name="companies")
    op.drop_index(op.f("ix_companies_created_at"), table_name="companies")
    op.drop_index(op.f("ix_companies_status"), table_name="companies")
    op.drop_table("companies")
