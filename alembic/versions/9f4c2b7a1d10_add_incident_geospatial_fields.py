"""add incident geospatial fields

Revision ID: 9f4c2b7a1d10
Revises: 763320853ecc
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "9f4c2b7a1d10"
down_revision: str | None = "763320853ecc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "incidents",
        sa.Column(
            "geospatial_status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "geospatial_enriched_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "census_tract_geoid",
            sa.String(length=11),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "census_tract_code",
            sa.String(length=6),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "census_tract_label",
            sa.String(length=20),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "borough_tract_code",
            sa.String(length=10),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "borough_code",
            sa.String(length=2),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "borough_name",
            sa.String(length=50),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "nta_code",
            sa.String(length=10),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "nta_name",
            sa.String(length=255),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "cdta_code",
            sa.String(length=10),
            nullable=True,
        ),
    )
    op.add_column(
        "incidents",
        sa.Column(
            "cdta_name",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_incidents_geospatial_status",
        "incidents",
        ["geospatial_status"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_census_tract_geoid",
        "incidents",
        ["census_tract_geoid"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_nta_code",
        "incidents",
        ["nta_code"],
        unique=False,
    )
    op.create_index(
        "ix_incidents_cdta_code",
        "incidents",
        ["cdta_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_incidents_cdta_code",
        table_name="incidents",
    )
    op.drop_index(
        "ix_incidents_nta_code",
        table_name="incidents",
    )
    op.drop_index(
        "ix_incidents_census_tract_geoid",
        table_name="incidents",
    )
    op.drop_index(
        "ix_incidents_geospatial_status",
        table_name="incidents",
    )

    op.drop_column("incidents", "cdta_name")
    op.drop_column("incidents", "cdta_code")
    op.drop_column("incidents", "nta_name")
    op.drop_column("incidents", "nta_code")
    op.drop_column("incidents", "borough_name")
    op.drop_column("incidents", "borough_code")
    op.drop_column("incidents", "borough_tract_code")
    op.drop_column("incidents", "census_tract_label")
    op.drop_column("incidents", "census_tract_code")
    op.drop_column("incidents", "census_tract_geoid")
    op.drop_column("incidents", "geospatial_enriched_at")
    op.drop_column("incidents", "geospatial_status")
