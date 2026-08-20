from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Integer,
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

    location: Mapped[WKBElement] = mapped_column(
        Geography(
            geometry_type="POINT",
            srid=4326,
            spatial_index=False,
        ),
        Computed(
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
    )

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

    weather_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        index=True,
    )
    weather_enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    weather_requested_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    weather_point_source: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    weather_forecast_source: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    nws_office: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        index=True,
    )
    nws_grid_id: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    nws_grid_x: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    nws_grid_y: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    weather_time_zone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    weather_radar_station: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    weather_forecast_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    weather_forecast_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    weather_forecast_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    weather_period_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    weather_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    weather_is_daytime: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    weather_temperature: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    weather_temperature_unit: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    weather_precipitation_probability_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    weather_relative_humidity_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    weather_dewpoint_value: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
    )
    weather_dewpoint_unit_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    weather_wind_speed: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    weather_wind_direction: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    weather_short_forecast: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    weather_detailed_forecast: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    weather_icon_url: Mapped[str | None] = mapped_column(
        Text,
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
