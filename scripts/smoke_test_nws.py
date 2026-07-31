import asyncio
from datetime import UTC, datetime

from app.integrations.nws.client import (
    NWSClient,
    NWSClientError,
)
from app.integrations.nws.resolver import (
    resolve_hourly_weather,
)


async def main() -> None:
    latitude = 40.7580
    longitude = -73.9855
    requested_at = datetime.now(UTC)

    print("Resolving hourly NWS weather...")

    try:
        async with NWSClient() as client:
            weather = await resolve_hourly_weather(
                client,
                latitude=latitude,
                longitude=longitude,
                at=requested_at,
            )

    except NWSClientError as exc:
        print(f"NWS smoke test failed: {exc}")
        raise SystemExit(1) from exc

    if weather is None:
        raise RuntimeError("No hourly forecast period contained the requested timestamp")

    print("NWS weather resolver completed.")
    print(f"  WFO: {weather.office}")
    print(f"  Grid: {weather.grid_id} {weather.grid_x},{weather.grid_y}")
    print(f"  Time zone: {weather.time_zone}")
    print(f"  Requested at: {weather.requested_at.isoformat()}")
    print(f"  Forecast updated: {weather.forecast_updated_at.isoformat()}")
    print(
        f"  Selected period: {weather.period_start.isoformat()} to {weather.period_end.isoformat()}"
    )
    print(f"  Temperature: {weather.temperature} {weather.temperature_unit}")
    print(f"  Precipitation probability: {weather.precipitation_probability_percent}%")
    print(f"  Relative humidity: {weather.relative_humidity_percent}%")
    print(f"  Wind: {weather.wind_speed} {weather.wind_direction}")
    print(f"  Conditions: {weather.short_forecast}")


if __name__ == "__main__":
    asyncio.run(main())
