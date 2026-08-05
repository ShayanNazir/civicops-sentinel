from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.nws.provider import (
    NWSHourlyForecastLoadResult,
    NWSPointLoadResult,
    NWSProvider,
)
from app.integrations.nws.resolver import (
    resolve_hourly_weather,
    select_forecast_period,
)
from app.integrations.nws.schemas import (
    NWSForecastPeriod,
    NWSHourlyForecastResponse,
    NWSPointResponse,
)


def build_period(
    *,
    number: int,
    start_time: str,
    end_time: str,
    temperature: float,
) -> NWSForecastPeriod:
    return NWSForecastPeriod.model_validate(
        {
            "number": number,
            "name": "",
            "startTime": start_time,
            "endTime": end_time,
            "isDaytime": True,
            "temperature": temperature,
            "temperatureUnit": "F",
            "temperatureTrend": None,
            "probabilityOfPrecipitation": {
                "unitCode": "wmoUnit:percent",
                "value": 20,
            },
            "dewpoint": {
                "unitCode": "wmoUnit:degC",
                "value": 19,
            },
            "relativeHumidity": {
                "unitCode": "wmoUnit:percent",
                "value": 60,
            },
            "windSpeed": "7 mph",
            "windDirection": "SW",
            "icon": ("https://api.weather.gov/icons/land/day/few"),
            "shortForecast": "Mostly Sunny",
            "detailedForecast": "",
        }
    )


def build_point_response() -> NWSPointResponse:
    return NWSPointResponse.model_validate(
        {
            "properties": {
                "cwa": "OKX",
                "gridId": "OKX",
                "gridX": 34,
                "gridY": 44,
                "forecast": ("https://api.weather.gov/gridpoints/OKX/34,44/forecast"),
                "forecastHourly": ("https://api.weather.gov/gridpoints/OKX/34,44/forecast/hourly"),
                "forecastGridData": ("https://api.weather.gov/gridpoints/OKX/34,44"),
                "observationStations": ("https://api.weather.gov/gridpoints/OKX/34,44/stations"),
                "timeZone": "America/New_York",
                "radarStation": "KOKX",
            }
        }
    )


def build_forecast_response(
    periods: list[NWSForecastPeriod],
) -> NWSHourlyForecastResponse:
    return NWSHourlyForecastResponse.model_validate(
        {
            "properties": {
                "units": "us",
                "forecastGenerator": ("HourlyForecastGenerator"),
                "generatedAt": ("2026-07-31T20:05:00+00:00"),
                "updateTime": ("2026-07-31T20:00:00+00:00"),
                "validTimes": ("2026-07-31T20:00:00+00:00/P7D"),
                "periods": [
                    period.model_dump(
                        by_alias=True,
                        mode="json",
                    )
                    for period in periods
                ],
            }
        }
    )


def test_selects_period_containing_timestamp() -> None:
    periods = [
        build_period(
            number=1,
            start_time=("2026-07-31T17:00:00-04:00"),
            end_time=("2026-07-31T18:00:00-04:00"),
            temperature=84,
        ),
        build_period(
            number=2,
            start_time=("2026-07-31T18:00:00-04:00"),
            end_time=("2026-07-31T19:00:00-04:00"),
            temperature=82,
        ),
    ]

    selected = select_forecast_period(
        periods,
        at=datetime(
            2026,
            7,
            31,
            21,
            30,
            tzinfo=UTC,
        ),
    )

    assert selected is not None
    assert selected.number == 1
    assert selected.temperature == 84


def test_period_end_uses_following_period() -> None:
    periods = [
        build_period(
            number=1,
            start_time=("2026-07-31T17:00:00-04:00"),
            end_time=("2026-07-31T18:00:00-04:00"),
            temperature=84,
        ),
        build_period(
            number=2,
            start_time=("2026-07-31T18:00:00-04:00"),
            end_time=("2026-07-31T19:00:00-04:00"),
            temperature=82,
        ),
    ]

    selected = select_forecast_period(
        periods,
        at=datetime(
            2026,
            7,
            31,
            22,
            0,
            tzinfo=UTC,
        ),
    )

    assert selected is not None
    assert selected.number == 2
    assert selected.temperature == 82


@pytest.mark.asyncio
async def test_resolver_returns_structured_weather() -> None:
    period = build_period(
        number=1,
        start_time=("2026-07-31T17:00:00-04:00"),
        end_time=("2026-07-31T18:00:00-04:00"),
        temperature=84,
    )

    provider = MagicMock(spec=NWSProvider)

    provider.get_point = AsyncMock(
        return_value=NWSPointLoadResult(
            response=build_point_response(),
            source="redis",
        )
    )

    provider.get_hourly_forecast = AsyncMock(
        return_value=NWSHourlyForecastLoadResult(
            response=build_forecast_response([period]),
            source="network",
        )
    )

    requested_at = datetime(
        2026,
        7,
        31,
        21,
        30,
        tzinfo=UTC,
    )

    weather = await resolve_hourly_weather(
        provider,
        latitude=40.7580,
        longitude=-73.9855,
        at=requested_at,
    )

    assert weather is not None

    assert weather.point_source == "redis"
    assert weather.forecast_source == "network"

    assert weather.office == "OKX"
    assert weather.grid_id == "OKX"
    assert weather.grid_x == 34
    assert weather.grid_y == 44

    assert weather.temperature == 84
    assert weather.temperature_unit == "F"

    assert weather.precipitation_probability_percent == 20
    assert weather.relative_humidity_percent == 60
    assert weather.wind_speed == "7 mph"
    assert weather.wind_direction == "SW"
    assert weather.short_forecast == "Mostly Sunny"

    provider.get_point.assert_awaited_once_with(
        latitude=40.7580,
        longitude=-73.9855,
    )

    provider.get_hourly_forecast.assert_awaited_once_with(
        forecast_url=("https://api.weather.gov/gridpoints/OKX/34,44/forecast/hourly")
    )


@pytest.mark.asyncio
async def test_resolver_returns_none_outside_range() -> None:
    period = build_period(
        number=1,
        start_time=("2026-07-31T17:00:00-04:00"),
        end_time=("2026-07-31T18:00:00-04:00"),
        temperature=84,
    )

    provider = MagicMock(spec=NWSProvider)

    provider.get_point = AsyncMock(
        return_value=NWSPointLoadResult(
            response=build_point_response(),
            source="redis",
        )
    )

    provider.get_hourly_forecast = AsyncMock(
        return_value=NWSHourlyForecastLoadResult(
            response=build_forecast_response([period]),
            source="redis",
        )
    )

    weather = await resolve_hourly_weather(
        provider,
        latitude=40.7580,
        longitude=-73.9855,
        at=datetime(
            2026,
            8,
            10,
            12,
            0,
            tzinfo=UTC,
        ),
    )

    assert weather is None

    provider.get_point.assert_awaited_once_with(
        latitude=40.7580,
        longitude=-73.9855,
    )

    provider.get_hourly_forecast.assert_awaited_once()
