"""add incident spatial location

Revision ID: f6a2b8d91c47
Revises: c2d8e1f4a903
"""

from collections.abc import Sequence

import sqlalchemy as sa
from geoalchemy2 import Geography

from alembic import op

revision: str = "f6a2b8d91c47"
down_revision: str | None = "c2d8e1f4a903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column(
            "location",
            Geography(
                geometry_type="POINT",
                srid=4326,
                spatial_index=False,
            ),
            sa.Computed(
                """
                ST_SetSRID(
                    ST_MakePoint(
                        longitude::double precision,
                        latitude::double precision
                    ),
                    4326
                )::geography
                """,
                persisted=True,
            ),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_incidents_location_gist",
        "incidents",
        ["location"],
        unique=False,
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incidents_location_gist",
        table_name="incidents",
    )

    op.drop_column(
        "incidents",
        "location",
    )
