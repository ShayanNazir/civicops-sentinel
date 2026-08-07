from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app
from app.repositories.incidents import IncidentRepository

client = TestClient(app)


def build_incident() -> SimpleNamespace:
    timestamp = datetime(
        2026,
        8,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    return SimpleNamespace(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        source="nyc311",
        external_id="12345678",
        description="Street condition: pothole",
        latitude=Decimal("40.758000"),
        longitude=Decimal("-73.985500"),
        media_urls=[],
        context_data={},
        status="received",
        priority="untriaged",
        geospatial_status="matched",
        geospatial_enriched_at=timestamp,
        census_tract_geoid="36061011900",
        census_tract_code="011900",
        census_tract_label="119",
        borough_tract_code="1011900",
        borough_code="1",
        borough_name="Manhattan",
        nta_code="MN0502",
        nta_name="Midtown-Times Square",
        cdta_code="MN05",
        cdta_name=("Midtown-Flatiron-Union Square (CD 5 Approximation)"),
        weather_status="matched",
        weather_enriched_at=timestamp,
        weather_requested_at=timestamp,
        weather_point_source="redis",
        weather_forecast_source="redis",
        nws_office="OKX",
        nws_grid_id="OKX",
        nws_grid_x=34,
        nws_grid_y=44,
        weather_time_zone="America/New_York",
        weather_radar_station="KOKX",
        weather_forecast_url=("https://api.weather.gov/gridpoints/OKX/34,44/forecast/hourly"),
        weather_forecast_updated_at=timestamp,
        weather_forecast_generated_at=timestamp,
        weather_period_start=timestamp,
        weather_period_end=datetime(
            2026,
            8,
            6,
            21,
            0,
            tzinfo=UTC,
        ),
        weather_is_daytime=True,
        weather_temperature=Decimal("82.00"),
        weather_temperature_unit="F",
        weather_precipitation_probability_percent=(Decimal("20.00")),
        weather_relative_humidity_percent=(Decimal("65.00")),
        weather_dewpoint_value=Decimal("19.00"),
        weather_dewpoint_unit_code="wmoUnit:degC",
        weather_wind_speed="5 mph",
        weather_wind_direction="SW",
        weather_short_forecast="Partly Cloudy",
        weather_detailed_forecast=("Partly cloudy with light southwest winds."),
        weather_icon_url=("https://api.weather.gov/icons/land/day/few"),
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_list_incidents_forwards_all_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_list = AsyncMock(return_value=[build_incident()])

    monkeypatch.setattr(
        IncidentRepository,
        "list",
        repository_list,
    )

    async def override_get_db():
        yield AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get(
            "/api/v1/incidents",
            params={
                "limit": 10,
                "offset": 5,
                "source": "nyc311",
                "borough": "Manhattan",
                "nta_code": "MN0502",
                "cdta_code": "MN05",
                "census_tract_geoid": ("36061011900"),
                "geospatial_status": "matched",
                "weather_status": "matched",
                "nws_office": "OKX",
                "min_temperature": "70",
                "max_temperature": "90",
                "min_precipitation_probability": "10",
                "max_precipitation_probability": "40",
                "weather_condition": "cloudy",
                "weather_is_daytime": "true",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 1
    assert payload[0]["borough_name"] == "Manhattan"
    assert payload[0]["weather_status"] == "matched"
    assert payload[0]["nws_office"] == "OKX"
    assert payload[0]["weather_temperature"] == "82.00"
    assert payload[0]["weather_short_forecast"] == "Partly Cloudy"

    repository_list.assert_awaited_once()

    call = repository_list.await_args

    assert call.kwargs == {
        "limit": 10,
        "offset": 5,
        "source": "nyc311",
        "borough": "Manhattan",
        "nta_code": "MN0502",
        "cdta_code": "MN05",
        "census_tract_geoid": "36061011900",
        "geospatial_status": "matched",
        "weather_status": "matched",
        "nws_office": "OKX",
        "min_temperature": Decimal("70"),
        "max_temperature": Decimal("90"),
        "min_precipitation_probability": (Decimal("10")),
        "max_precipitation_probability": (Decimal("40")),
        "weather_condition": "cloudy",
        "weather_is_daytime": True,
    }


def test_list_incidents_rejects_invalid_geospatial_status() -> None:
    response = client.get(
        "/api/v1/incidents",
        params={
            "geospatial_status": "finished",
        },
    )

    assert response.status_code == 422


def test_list_incidents_rejects_invalid_weather_status() -> None:
    response = client.get(
        "/api/v1/incidents",
        params={
            "weather_status": "finished",
        },
    )

    assert response.status_code == 422


def test_list_incidents_rejects_reversed_temperature_range() -> None:
    response = client.get(
        "/api/v1/incidents",
        params={
            "min_temperature": "90",
            "max_temperature": "70",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == ("min_temperature cannot be greater than max_temperature.")
