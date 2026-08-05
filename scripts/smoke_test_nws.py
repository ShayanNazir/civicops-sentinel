import asyncio
from datetime import UTC, datetime

from app.integrations.nws.cache import NWSCache
from app.integrations.nws.client import (
    NWSClient,
    NWSClientError,
)
from app.integrations.nws.provider import NWSProvider
from app.integrations.nws.resolver import (
    resolve_hourly_weather,
)


async def main() -> None:
    latitude = 40.7580
    longitude = -73.9855
    requested_at = datetime.now(UTC)

    print("Resolving cached hourly NWS weather...")

    try:
        async with NWSClient() as client:
            async with NWSCache() as cache:
                provider = NWSProvider(
                    client=client,
                    cache=cache,
                )

                first = await resolve_hourly_weather(
                    provider,
                    latitude=latitude,
                    longitude=longitude,
                    at=requested_at,
                )

                second = await resolve_hourly_weather(
                    provider,
                    latitude=latitude,
                    longitude=longitude,
                    at=requested_at,
                )

    except NWSClientError as exc:
        print(f"NWS smoke test failed: {exc}")
        raise SystemExit(1) from exc

    if first is None or second is None:
        raise RuntimeError("No hourly forecast period contained the requested timestamp")

    print("Cached NWS weather resolver completed.")

    print(f"  Initial sources: point={first.point_source}, forecast={first.forecast_source}")

    print(f"  Second sources: point={second.point_source}, forecast={second.forecast_source}")

    print(f"  WFO: {second.office}")

    print(f"  Grid: {second.grid_id} {second.grid_x},{second.grid_y}")

    print(
        f"  Selected period: {second.period_start.isoformat()} to {second.period_end.isoformat()}"
    )

    print(f"  Temperature: {second.temperature} {second.temperature_unit}")

    print(f"  Precipitation probability: {second.precipitation_probability_percent}%")

    print(f"  Relative humidity: {second.relative_humidity_percent}%")

    print(f"  Wind: {second.wind_speed} {second.wind_direction}")

    print(f"  Conditions: {second.short_forecast}")


if __name__ == "__main__":
    asyncio.run(main())
