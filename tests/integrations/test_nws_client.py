import httpx
import pytest

from app.core.config import Settings
from app.integrations.nws.client import NWSClient


def build_point_response() -> dict:
    return {
        "properties": {
            "cwa": "OKX",
            "gridId": "OKX",
            "gridX": 33,
            "gridY": 37,
            "forecast": ("https://api.weather.gov/gridpoints/OKX/33,37/forecast"),
            "forecastHourly": ("https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"),
            "forecastGridData": ("https://api.weather.gov/gridpoints/OKX/33,37"),
            "observationStations": ("https://api.weather.gov/gridpoints/OKX/33,37/stations"),
            "timeZone": "America/New_York",
            "radarStation": "KOKX",
        }
    }


def build_hourly_response() -> dict:
    return {
        "properties": {
            "units": "us",
            "forecastGenerator": ("HourlyForecastGenerator"),
            "generatedAt": ("2026-07-31T20:05:00+00:00"),
            "updateTime": ("2026-07-31T20:00:00+00:00"),
            "validTimes": ("2026-07-31T20:00:00+00:00/P7D"),
            "periods": [
                {
                    "number": 1,
                    "name": "",
                    "startTime": ("2026-07-31T17:00:00-04:00"),
                    "endTime": ("2026-07-31T18:00:00-04:00"),
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
                        "value": 20,
                    },
                    "relativeHumidity": {
                        "unitCode": "wmoUnit:percent",
                        "value": 55,
                    },
                    "windSpeed": "8 mph",
                    "windDirection": "SW",
                    "icon": ("https://api.weather.gov/icons/land/day/few"),
                    "shortForecast": ("Mostly Sunny"),
                    "detailedForecast": "",
                }
            ],
        }
    }


@pytest.mark.asyncio
async def test_fetch_point_returns_validated_metadata() -> None:
    settings = Settings()

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == ("/points/40.7580,-73.9855")
        assert request.headers["User-Agent"] == settings.nws_user_agent
        assert request.headers["Accept"] == "application/geo+json"

        return httpx.Response(
            status_code=200,
            json=build_point_response(),
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NWSClient(
            settings=settings,
            client=http_client,
        )

        point = await client.fetch_point(
            latitude=40.7580,
            longitude=-73.9855,
        )

    assert point.properties.cwa == "OKX"
    assert point.properties.grid_id == "OKX"
    assert point.properties.grid_x == 33
    assert point.properties.grid_y == 37
    assert point.properties.forecast_hourly_url == (
        "https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"
    )


@pytest.mark.asyncio
async def test_fetch_hourly_forecast_returns_periods() -> None:
    forecast_url = "https://api.weather.gov/gridpoints/OKX/33,37/forecast/hourly"

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert str(request.url) == forecast_url

        return httpx.Response(
            status_code=200,
            json=build_hourly_response(),
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NWSClient(
            settings=Settings(),
            client=http_client,
        )

        forecast = await client.fetch_hourly_forecast(
            forecast_url=forecast_url,
        )

    period = forecast.properties.periods[0]

    assert period.temperature == 84
    assert period.temperature_unit == "F"
    assert period.wind_speed == "8 mph"
    assert period.wind_direction == "SW"
    assert period.short_forecast == "Mostly Sunny"

    assert period.probability_of_precipitation is not None
    assert period.probability_of_precipitation.value == 20

    assert period.relative_humidity is not None
    assert period.relative_humidity.value == 55


@pytest.mark.asyncio
async def test_fetch_point_retries_temporary_failure() -> None:
    attempts = 0

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            return httpx.Response(
                status_code=503,
                json={"detail": "Temporarily unavailable"},
            )

        return httpx.Response(
            status_code=200,
            json=build_point_response(),
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NWSClient(
            settings=Settings(),
            client=http_client,
            max_retries=1,
            retry_base_delay=0,
        )

        point = await client.fetch_point(
            latitude=40.7580,
            longitude=-73.9855,
        )

    assert attempts == 2
    assert point.properties.grid_id == "OKX"


@pytest.mark.asyncio
async def test_client_rejects_invalid_inputs() -> None:
    async with NWSClient(settings=Settings()) as client:
        with pytest.raises(
            ValueError,
            match="latitude",
        ):
            await client.fetch_point(
                latitude=100,
                longitude=-73.9855,
            )

        with pytest.raises(
            ValueError,
            match="configured NWS API host",
        ):
            await client.fetch_hourly_forecast(
                forecast_url=("https://example.com/forecast"),
            )
