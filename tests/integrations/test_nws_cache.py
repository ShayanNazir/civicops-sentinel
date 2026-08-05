from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.integrations.nws.cache import NWSCache
from app.integrations.nws.client import NWSClient
from app.integrations.nws.provider import NWSProvider
from app.integrations.nws.schemas import (
    NWSHourlyForecastResponse,
    NWSPointResponse,
)


def build_settings() -> Settings:
    return Settings(
        redis_url="redis://redis:6379/0",
        nws_point_cache_ttl_seconds=3600,
        nws_hourly_forecast_cache_ttl_seconds=300,
    )


def build_point() -> NWSPointResponse:
    return NWSPointResponse.model_validate(
        {
            "properties": {
                "cwa": "OKX",
                "gridId": "OKX",
                "gridX": 34,
                "gridY": 44,
                "forecast": (
                    "https://api.weather.gov/"
                    "gridpoints/OKX/34,44/forecast"
                ),
                "forecastHourly": (
                    "https://api.weather.gov/"
                    "gridpoints/OKX/34,44/"
                    "forecast/hourly"
                ),
                "forecastGridData": (
                    "https://api.weather.gov/"
                    "gridpoints/OKX/34,44"
                ),
                "observationStations": (
                    "https://api.weather.gov/"
                    "gridpoints/OKX/34,44/stations"
                ),
                "timeZone": "America/New_York",
                "radarStation": "KOKX",
            }
        }
    )


def build_forecast() -> NWSHourlyForecastResponse:
    return NWSHourlyForecastResponse.model_validate(
        {
            "properties": {
                "units": "us",
                "generatedAt": (
                    "2026-07-31T20:05:00+00:00"
                ),
                "updateTime": (
                    "2026-07-31T20:00:00+00:00"
                ),
                "periods": [
                    {
                        "number": 1,
                        "name": "",
                        "startTime": (
                            "2026-07-31T17:00:00-04:00"
                        ),
                        "endTime": (
                            "2026-07-31T18:00:00-04:00"
                        ),
                        "isDaytime": True,
                        "temperature": 84,
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
                        "icon": (
                            "https://api.weather.gov/"
                            "icons/land/day/few"
                        ),
                        "shortForecast": "Mostly Sunny",
                        "detailedForecast": "",
                    }
                ],
            }
        }
    )


@pytest.mark.asyncio
async def test_cache_returns_valid_point() -> None:
    point = build_point()

    redis_client = AsyncMock()
    redis_client.get.return_value = (
        point.model_dump_json(by_alias=True)
    )

    cache = NWSCache(
        settings=build_settings(),
        client=redis_client,
    )

    result = await cache.get_point(
        latitude=40.7580,
        longitude=-73.9855,
    )

    assert result is not None
    assert result.properties.grid_id == "OKX"

    redis_client.get.assert_awaited_once_with(
        cache.point_cache_key(
            latitude=40.7580,
            longitude=-73.9855,
        )
    )


@pytest.mark.asyncio
async def test_cache_removes_corrupted_forecast() -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = "invalid JSON"

    cache = NWSCache(
        settings=build_settings(),
        client=redis_client,
    )

    forecast_url = (
        "https://api.weather.gov/"
        "gridpoints/OKX/34,44/forecast/hourly"
    )

    result = await cache.get_hourly_forecast(
        forecast_url=forecast_url,
    )

    assert result is None

    redis_client.delete.assert_awaited_once_with(
        cache.hourly_forecast_cache_key(
            forecast_url
        )
    )


@pytest.mark.asyncio
async def test_provider_fetches_and_caches_point() -> None:
    point = build_point()

    client = MagicMock(spec=NWSClient)
    client.fetch_point = AsyncMock(
        return_value=point
    )

    cache = MagicMock(spec=NWSCache)
    cache.get_point = AsyncMock(
        side_effect=[None, None]
    )
    cache.set_point = AsyncMock(
        return_value=True
    )

    provider = NWSProvider(
        client=client,
        cache=cache,
    )

    result = await provider.get_point(
        latitude=40.7580,
        longitude=-73.9855,
    )

    assert result.source == "network"
    assert result.response is point

    client.fetch_point.assert_awaited_once_with(
        latitude=40.7580,
        longitude=-73.9855,
    )

    cache.set_point.assert_awaited_once_with(
        latitude=40.7580,
        longitude=-73.9855,
        point=point,
    )


@pytest.mark.asyncio
async def test_provider_uses_cached_point() -> None:
    point = build_point()

    client = MagicMock(spec=NWSClient)
    client.fetch_point = AsyncMock()

    cache = MagicMock(spec=NWSCache)
    cache.get_point = AsyncMock(
        return_value=point
    )
    cache.set_point = AsyncMock()

    provider = NWSProvider(
        client=client,
        cache=cache,
    )

    result = await provider.get_point(
        latitude=40.7580,
        longitude=-73.9855,
    )

    assert result.source == "redis"
    assert result.response is point

    client.fetch_point.assert_not_awaited()
    cache.set_point.assert_not_awaited()


@pytest.mark.asyncio
async def test_provider_uses_cached_forecast() -> None:
    forecast = build_forecast()

    client = MagicMock(spec=NWSClient)
    client.fetch_hourly_forecast = AsyncMock()

    cache = MagicMock(spec=NWSCache)
    cache.get_hourly_forecast = AsyncMock(
        return_value=forecast
    )
    cache.set_hourly_forecast = AsyncMock()

    provider = NWSProvider(
        client=client,
        cache=cache,
    )

    forecast_url = (
        "https://api.weather.gov/"
        "gridpoints/OKX/34,44/forecast/hourly"
    )

    result = await provider.get_hourly_forecast(
        forecast_url=forecast_url,
    )

    assert result.source == "redis"
    assert result.response is forecast

    client.fetch_hourly_forecast.assert_not_awaited()
    cache.set_hourly_forecast.assert_not_awaited()