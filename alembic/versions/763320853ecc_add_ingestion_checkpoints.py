"""add ingestion checkpoints

Revision ID: 763320853ecc
Revises: 0001
Create Date: 2026-07-25 04:44:17.461549
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "763320853ecc"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ingestion_checkpoints",
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column(
            "last_successful_created_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_run_started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_run_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "last_status",
            sa.String(length=20),
            server_default="never",
            nullable=False,
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "total_records_fetched",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "total_records_upserted",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_checkpoints")
