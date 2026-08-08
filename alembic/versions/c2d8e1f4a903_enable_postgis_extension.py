"""enable postgis extension

Revision ID: c2d8e1f4a903
Revises: b7f31d9c4a62
"""

from collections.abc import Sequence

from alembic import op

revision: str = "c2d8e1f4a903"
down_revision: str | None = "b7f31d9c4a62"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE EXTENSION IF NOT EXISTS postgis"
    )


def downgrade() -> None:
    op.execute(
        "DROP EXTENSION IF EXISTS postgis"
    )