from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.resolver import (
    ResolvedHourlyWeather,
)
from app.integrations.nyc_boundaries.index import NYCGeography
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


def decimal_or_none(
    value: float | None,
) -> Decimal | None:
    """Convert an optional float to a database-safe Decimal."""

    if value is None:
        return None

    return Decimal(str(value))


class IncidentRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        payload: IncidentCreate,
    ) -> Incident:
        incident = Incident(**payload.model_dump())
        db.add(incident)

        await db.commit()
        await db.refresh(incident)

        return incident

    @staticmethod
    async def get(
        db: AsyncSession,
        incident_id: UUID,
    ) -> Incident | None:
        return await db.get(
            Incident,
            incident_id,
        )

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
        source: str | None = None,
        borough: str | None = None,
        nta_code: str | None = None,
        cdta_code: str | None = None,
        census_tract_geoid: str | None = None,
        geospatial_status: str | None = None,
    ) -> list[Incident]:
        """List incidents using optional geographic filters."""

        statement = select(Incident)

        if source is not None:
            statement = statement.where(Incident.source == source)

        if borough is not None:
            statement = statement.where(Incident.borough_name == borough)

        if nta_code is not None:
            statement = statement.where(Incident.nta_code == nta_code)

        if cdta_code is not None:
            statement = statement.where(Incident.cdta_code == cdta_code)

        if census_tract_geoid is not None:
            statement = statement.where(Incident.census_tract_geoid == census_tract_geoid)

        if geospatial_status is not None:
            statement = statement.where(Incident.geospatial_status == geospatial_status)

        statement = (
            statement.order_by(
                Incident.created_at.desc(),
                Incident.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        result = await db.execute(statement)

        return list(result.scalars().all())

    @staticmethod
    async def upsert_many(
        db: AsyncSession,
        rows: Sequence[dict[str, Any]],
    ) -> int:
        """
        Insert new incidents or update existing incidents.

        The database uniqueness constraint on source and external_id
        prevents repeated ingestion from creating duplicate records.
        """

        if not rows:
            return 0

        insert_statement = insert(Incident).values(list(rows))

        upsert_statement = insert_statement.on_conflict_do_update(
            constraint=("uq_incident_source_external_id"),
            set_={
                "description": (insert_statement.excluded.description),
                "latitude": (insert_statement.excluded.latitude),
                "longitude": (insert_statement.excluded.longitude),
                "media_urls": (insert_statement.excluded.media_urls),
                "status": (insert_statement.excluded.status),
                "priority": (insert_statement.excluded.priority),
                "context_data": (insert_statement.excluded.context_data),
                "updated_at": func.now(),
            },
        )

        await db.execute(upsert_statement)
        await db.commit()

        return len(rows)

    @staticmethod
    async def list_pending_geospatial(
        db: AsyncSession,
        *,
        limit: int,
    ) -> list[Incident]:
        """
        Select pending incidents for geospatial enrichment.

        Locked rows are skipped so multiple workers can safely
        process separate batches.
        """

        if limit < 1:
            raise ValueError("limit must be at least 1")

        result = await db.execute(
            select(Incident)
            .where(Incident.geospatial_status == "pending")
            .order_by(
                Incident.created_at.asc(),
                Incident.id.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(result.scalars().all())

    @staticmethod
    async def save_geospatial_results(
        db: AsyncSession,
        resolutions: Sequence[tuple[Incident, NYCGeography | None]],
        *,
        enriched_at: datetime,
    ) -> None:
        """Save matched or unmatched geography for a batch."""

        for incident, geography in resolutions:
            incident.geospatial_enriched_at = enriched_at

            if geography is None:
                incident.geospatial_status = "unmatched"
                incident.census_tract_geoid = None
                incident.census_tract_code = None
                incident.census_tract_label = None
                incident.borough_tract_code = None
                incident.borough_code = None
                incident.borough_name = None
                incident.nta_code = None
                incident.nta_name = None
                incident.cdta_code = None
                incident.cdta_name = None
                continue

            incident.geospatial_status = "matched"
            incident.census_tract_geoid = geography.census_tract_geoid
            incident.census_tract_code = geography.census_tract_code
            incident.census_tract_label = geography.census_tract_label
            incident.borough_tract_code = geography.borough_tract_code
            incident.borough_code = geography.borough_code
            incident.borough_name = geography.borough_name
            incident.nta_code = geography.nta_code
            incident.nta_name = geography.nta_name
            incident.cdta_code = geography.cdta_code
            incident.cdta_name = geography.cdta_name

        await db.commit()

    @staticmethod
    async def list_pending_weather(
        db: AsyncSession,
        *,
        limit: int,
    ) -> list[Incident]:
        """
        Select pending incidents for weather enrichment.

        Locked rows are skipped so multiple workers can safely
        process separate batches.
        """

        if limit < 1:
            raise ValueError("limit must be at least 1")

        result = await db.execute(
            select(Incident)
            .where(Incident.weather_status == "pending")
            .order_by(
                Incident.created_at.asc(),
                Incident.id.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(result.scalars().all())

    @staticmethod
    def clear_weather_fields(
        incident: Incident,
    ) -> None:
        """Clear previously stored weather values."""

        incident.weather_point_source = None
        incident.weather_forecast_source = None

        incident.nws_office = None
        incident.nws_grid_id = None
        incident.nws_grid_x = None
        incident.nws_grid_y = None
        incident.weather_time_zone = None
        incident.weather_radar_station = None

        incident.weather_forecast_url = None
        incident.weather_forecast_updated_at = None
        incident.weather_forecast_generated_at = None

        incident.weather_period_start = None
        incident.weather_period_end = None
        incident.weather_is_daytime = None

        incident.weather_temperature = None
        incident.weather_temperature_unit = None
        incident.weather_precipitation_probability_percent = None
        incident.weather_relative_humidity_percent = None
        incident.weather_dewpoint_value = None
        incident.weather_dewpoint_unit_code = None

        incident.weather_wind_speed = None
        incident.weather_wind_direction = None
        incident.weather_short_forecast = None
        incident.weather_detailed_forecast = None
        incident.weather_icon_url = None

    @staticmethod
    async def save_weather_results(
        db: AsyncSession,
        resolutions: Sequence[
            tuple[
                Incident,
                ResolvedHourlyWeather | None,
            ]
        ],
        *,
        enriched_at: datetime,
    ) -> None:
        """Save matched or unavailable weather results."""

        for incident, weather in resolutions:
            incident.weather_enriched_at = enriched_at

            if weather is None:
                incident.weather_status = "unavailable"
                incident.weather_requested_at = enriched_at

                IncidentRepository.clear_weather_fields(incident)
                continue

            incident.weather_status = "matched"
            incident.weather_requested_at = weather.requested_at

            incident.weather_point_source = weather.point_source
            incident.weather_forecast_source = weather.forecast_source

            incident.nws_office = weather.office
            incident.nws_grid_id = weather.grid_id
            incident.nws_grid_x = weather.grid_x
            incident.nws_grid_y = weather.grid_y
            incident.weather_time_zone = weather.time_zone
            incident.weather_radar_station = weather.radar_station

            incident.weather_forecast_url = weather.forecast_url
            incident.weather_forecast_updated_at = weather.forecast_updated_at
            incident.weather_forecast_generated_at = weather.forecast_generated_at

            incident.weather_period_start = weather.period_start
            incident.weather_period_end = weather.period_end
            incident.weather_is_daytime = weather.is_daytime

            incident.weather_temperature = decimal_or_none(weather.temperature)
            incident.weather_temperature_unit = weather.temperature_unit
            incident.weather_precipitation_probability_percent = decimal_or_none(
                weather.precipitation_probability_percent
            )
            incident.weather_relative_humidity_percent = decimal_or_none(
                weather.relative_humidity_percent
            )
            incident.weather_dewpoint_value = decimal_or_none(weather.dewpoint_value)
            incident.weather_dewpoint_unit_code = weather.dewpoint_unit_code

            incident.weather_wind_speed = weather.wind_speed
            incident.weather_wind_direction = weather.wind_direction
            incident.weather_short_forecast = weather.short_forecast
            incident.weather_detailed_forecast = weather.detailed_forecast
            incident.weather_icon_url = weather.icon_url

        await db.commit()
