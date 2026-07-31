import asyncio

from app.integrations.nws.client import (
    NWSClient,
    NWSClientError,
)


async def main() -> None:
    latitude = 40.7580
    longitude = -73.9855

    print("Loading NWS point metadata...")

    try:
        async with NWSClient() as client:
            point = await client.fetch_point(
                latitude=latitude,
                longitude=longitude,
            )

            forecast = (
                await client.fetch_hourly_forecast(
                    forecast_url=(
                        point.properties
                        .forecast_hourly_url
                    ),
                )
            )

    except NWSClientError as exc:
        print(f"NWS smoke test failed: {exc}")
        raise SystemExit(1) from exc

    if not forecast.properties.periods:
        raise RuntimeError(
            "NWS returned no hourly forecast periods"
        )

    first_period = forecast.properties.periods[0]
    precipitation = (
        first_period
        .probability_of_precipitation
    )

    precipitation_value = (
        precipitation.value
        if precipitation is not None
        else None
    )

    print("NWS smoke test completed.")
    print(f"  WFO: {point.properties.cwa}")
    print(
        "  Grid: "
        f"{point.properties.grid_id} "
        f"{point.properties.grid_x},"
        f"{point.properties.grid_y}"
    )
    print(
        "  Time zone: "
        f"{point.properties.time_zone}"
    )
    print(
        "  Forecast updated: "
        f"{forecast.properties.update_time.isoformat()}"
    )
    print(
        "  First period: "
        f"{first_period.start_time.isoformat()}"
    )
    print(
        "  Temperature: "
        f"{first_period.temperature} "
        f"{first_period.temperature_unit}"
    )
    print(
        "  Precipitation probability: "
        f"{precipitation_value}%"
    )
    print(
        "  Wind: "
        f"{first_period.wind_speed} "
        f"{first_period.wind_direction}"
    )
    print(
        "  Conditions: "
        f"{first_period.short_forecast}"
    )


if __name__ == "__main__":
    asyncio.run(main())