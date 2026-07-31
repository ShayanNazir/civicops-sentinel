from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_incident_source_external_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    source: Mapped[str] = mapped_column(
        String(50),
        default="manual",
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(Text)
    latitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    media_urls: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="received",
        index=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="untriaged",
    )
    context_data: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    geospatial_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        index=True,
    )
    geospatial_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    census_tract_geoid: Mapped[str | None] = mapped_column(
        String(11),
        nullable=True,
        index=True,
    )
    census_tract_code: Mapped[str | None] = mapped_column(
        String(6),
        nullable=True,
    )
    census_tract_label: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    borough_tract_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    borough_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    borough_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    nta_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    nta_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    cdta_code: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    cdta_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
