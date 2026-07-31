from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from app.integrations.nws.client import NWSClient
from app.integrations.nws.schemas import (
    NWSForecastPeriod,
    NWSQuantitativeValue,
)


@dataclass(frozen=True, slots=True)
class ResolvedHourlyWeather:
    """Weather forecast resolved for one coordinate and time."""

    requested_at: datetime

    office: str
    grid_id: str
    grid_x: int
    grid_y: int
    time_zone: str
    radar_station: str | None

    forecast_url: str
    forecast_updated_at: datetime
    forecast_generated_at: datetime | None

    period_start: datetime
    period_end: datetime
    is_daytime: bool

    temperature: float
    temperature_unit: str

    precipitation_probability_percent: float | None
    relative_humidity_percent: float | None
    dewpoint_value: float | None
    dewpoint_unit_code: str | None

    wind_speed: str
    wind_direction: str

    short_forecast: str
    detailed_forecast: str
    icon_url: str


def normalize_utc(value: datetime) -> datetime:
    """Normalize a timestamp to timezone-aware UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def measurement_value(
    measurement: NWSQuantitativeValue | None,
) -> float | None:
    """Extract the numeric value from an NWS measurement."""

    if measurement is None:
        return None

    return measurement.value


def select_forecast_period(
    periods: Sequence[NWSForecastPeriod],
    *,
    at: datetime,
) -> NWSForecastPeriod | None:
    """Select the period containing the requested timestamp."""

    resolved_at = normalize_utc(at)

    for period in periods:
        period_start = normalize_utc(period.start_time)
        period_end = normalize_utc(period.end_time)

        if period_start <= resolved_at < period_end:
            return period

    return None


async def resolve_hourly_weather(
    client: NWSClient,
    *,
    latitude: float,
    longitude: float,
    at: datetime | None = None,
) -> ResolvedHourlyWeather | None:
    """Resolve an hourly NWS forecast for a coordinate."""

    requested_at = normalize_utc(at or datetime.now(UTC))

    point = await client.fetch_point(
        latitude=latitude,
        longitude=longitude,
    )

    forecast_url = point.properties.forecast_hourly_url

    forecast = await client.fetch_hourly_forecast(
        forecast_url=forecast_url,
    )

    period = select_forecast_period(
        forecast.properties.periods,
        at=requested_at,
    )

    if period is None:
        return None

    precipitation = period.probability_of_precipitation
    humidity = period.relative_humidity
    dewpoint = period.dewpoint

    generated_at = forecast.properties.generated_at

    return ResolvedHourlyWeather(
        requested_at=requested_at,
        office=point.properties.cwa,
        grid_id=point.properties.grid_id,
        grid_x=point.properties.grid_x,
        grid_y=point.properties.grid_y,
        time_zone=point.properties.time_zone,
        radar_station=point.properties.radar_station,
        forecast_url=forecast_url,
        forecast_updated_at=normalize_utc(forecast.properties.update_time),
        forecast_generated_at=(normalize_utc(generated_at) if generated_at is not None else None),
        period_start=normalize_utc(period.start_time),
        period_end=normalize_utc(period.end_time),
        is_daytime=period.is_daytime,
        temperature=period.temperature,
        temperature_unit=period.temperature_unit,
        precipitation_probability_percent=(measurement_value(precipitation)),
        relative_humidity_percent=(measurement_value(humidity)),
        dewpoint_value=measurement_value(dewpoint),
        dewpoint_unit_code=(dewpoint.unit_code if dewpoint is not None else None),
        wind_speed=period.wind_speed,
        wind_direction=period.wind_direction,
        short_forecast=period.short_forecast,
        detailed_forecast=(period.detailed_forecast),
        icon_url=period.icon,
    )
