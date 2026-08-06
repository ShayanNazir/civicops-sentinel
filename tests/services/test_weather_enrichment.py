from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.client import NWSNotFoundError
from app.integrations.nws.provider import NWSProvider
from app.integrations.nws.resolver import (
    ResolvedHourlyWeather,
)
from app.models.incident import Incident
from app.repositories.incidents import IncidentRepository
from app.services import weather_enrichment as weather_module


def build_incident(
    external_id: str,
    *,
    latitude: str,
    longitude: str,
) -> Incident:
    return Incident(
        source="nyc311",
        external_id=external_id,
        description="Test street condition incident",
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        media_urls=[],
        context_data={},
    )


def build_weather(
    requested_at: datetime,
) -> ResolvedHourlyWeather:
    return ResolvedHourlyWeather(
        requested_at=requested_at,
        point_source="redis",
        forecast_source="network",
        office="OKX",
        grid_id="OKX",
        grid_x=34,
        grid_y=44,
        time_zone="America/New_York",
        radar_station="KOKX",
        forecast_url=("https://api.weather.gov/gridpoints/OKX/34,44/forecast/hourly"),
        forecast_updated_at=datetime(
            2026,
            8,
            5,
            4,
            0,
            tzinfo=UTC,
        ),
        forecast_generated_at=datetime(
            2026,
            8,
            5,
            4,
            5,
            tzinfo=UTC,
        ),
        period_start=datetime(
            2026,
            8,
            5,
            4,
            0,
            tzinfo=UTC,
        ),
        period_end=datetime(
            2026,
            8,
            5,
            5,
            0,
            tzinfo=UTC,
        ),
        is_daytime=False,
        temperature=76,
        temperature_unit="F",
        precipitation_probability_percent=20,
        relative_humidity_percent=68,
        dewpoint_value=19,
        dewpoint_unit_code="wmoUnit:degC",
        wind_speed="5 mph",
        wind_direction="NE",
        short_forecast="Partly Cloudy",
        detailed_forecast="",
        icon_url=("https://api.weather.gov/icons/land/night/few"),
    )


def build_db() -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_weather_enrichment_matches_and_marks_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()

    matched_incident = build_incident(
        "2001",
        latitude="40.758000",
        longitude="-73.985500",
    )
    unavailable_incident = build_incident(
        "2002",
        latitude="40.712800",
        longitude="-74.006000",
    )

    enriched_at = datetime(
        2026,
        8,
        5,
        4,
        30,
        tzinfo=UTC,
    )

    resolved_weather = build_weather(enriched_at)

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_weather",
        AsyncMock(
            return_value=[
                matched_incident,
                unavailable_incident,
            ]
        ),
    )

    resolve_weather = AsyncMock(
        side_effect=[
            resolved_weather,
            None,
        ]
    )

    monkeypatch.setattr(
        weather_module,
        "resolve_hourly_weather",
        resolve_weather,
    )

    provider = MagicMock(spec=NWSProvider)

    result = await weather_module.enrich_pending_weather_incidents(
        db,
        provider,
        limit=100,
        enriched_at=enriched_at,
    )

    assert result.selected == 2
    assert result.matched == 1
    assert result.unavailable == 1
    assert result.enriched_at == enriched_at

    assert matched_incident.weather_status == "matched"
    assert matched_incident.nws_office == "OKX"
    assert matched_incident.nws_grid_x == 34
    assert matched_incident.nws_grid_y == 44

    assert matched_incident.weather_temperature == Decimal("76")
    assert matched_incident.weather_precipitation_probability_percent == Decimal("20")
    assert matched_incident.weather_short_forecast == "Partly Cloudy"
    assert matched_incident.weather_point_source == "redis"
    assert matched_incident.weather_forecast_source == "network"
    assert matched_incident.weather_enriched_at == enriched_at

    assert unavailable_incident.weather_status == "unavailable"
    assert unavailable_incident.weather_requested_at == enriched_at
    assert unavailable_incident.weather_temperature is None
    assert unavailable_incident.weather_short_forecast is None

    assert resolve_weather.await_count == 2

    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_weather_enrichment_handles_empty_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()
    provider = MagicMock(spec=NWSProvider)

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_weather",
        AsyncMock(return_value=[]),
    )

    resolve_weather = AsyncMock()

    monkeypatch.setattr(
        weather_module,
        "resolve_hourly_weather",
        resolve_weather,
    )

    result = await weather_module.enrich_pending_weather_incidents(
        db,
        provider,
    )

    assert result.selected == 0
    assert result.matched == 0
    assert result.unavailable == 0

    resolve_weather.assert_not_awaited()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_weather_enrichment_rolls_back_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()
    db.commit.side_effect = RuntimeError("Database commit failed")

    incident = build_incident(
        "2003",
        latitude="40.758000",
        longitude="-73.985500",
    )

    enriched_at = datetime(
        2026,
        8,
        5,
        4,
        30,
        tzinfo=UTC,
    )

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_weather",
        AsyncMock(return_value=[incident]),
    )

    monkeypatch.setattr(
        weather_module,
        "resolve_hourly_weather",
        AsyncMock(return_value=build_weather(enriched_at)),
    )

    provider = MagicMock(spec=NWSProvider)

    with pytest.raises(
        RuntimeError,
        match="Database commit failed",
    ):
        await weather_module.enrich_pending_weather_incidents(
            db,
            provider,
            enriched_at=enriched_at,
        )

    db.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_weather_enrichment_marks_nws_404_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()

    incident = build_incident(
        "unsupported-location",
        latitude="-90.000000",
        longitude="-180.000000",
    )

    enriched_at = datetime(
        2026,
        8,
        6,
        18,
        0,
        tzinfo=UTC,
    )

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_weather",
        AsyncMock(return_value=[incident]),
    )

    monkeypatch.setattr(
        weather_module,
        "resolve_hourly_weather",
        AsyncMock(side_effect=NWSNotFoundError("NWS forecast resource was not found.")),
    )

    provider = MagicMock(spec=NWSProvider)

    result = await weather_module.enrich_pending_weather_incidents(
        db,
        provider,
        enriched_at=enriched_at,
    )

    assert result.selected == 1
    assert result.matched == 0
    assert result.unavailable == 1

    assert incident.weather_status == "unavailable"
    assert incident.weather_requested_at == enriched_at
    assert incident.weather_temperature is None

    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
