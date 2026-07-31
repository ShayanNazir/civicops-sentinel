import asyncio

from app.integrations.nyc_boundaries.cache import (
    NYCBoundaryCache,
)
from app.integrations.nyc_boundaries.client import (
    NYCBoundaryClient,
    NYCBoundaryClientError,
)
from app.integrations.nyc_boundaries.provider import (
    NYCBoundaryIndexProvider,
)

# Times Square
TEST_LATITUDE = 40.7580
TEST_LONGITUDE = -73.9855


async def main() -> None:
    print("Loading NYC boundary spatial index...")

    try:
        async with NYCBoundaryClient() as client:
            async with NYCBoundaryCache() as cache:
                provider = NYCBoundaryIndexProvider(
                    client=client,
                    cache=cache,
                )

                first_result = await provider.get_index()

                geography = first_result.index.resolve(
                    latitude=TEST_LATITUDE,
                    longitude=TEST_LONGITUDE,
                )

                if geography is None:
                    raise RuntimeError("The test coordinate did not resolve to an NYC boundary")

                second_result = await provider.get_index()

    except NYCBoundaryClientError as exc:
        print(f"Boundary request failed: {exc}")
        raise SystemExit(1) from exc

    print("NYC boundary smoke test completed.")
    print(f"  Indexed polygons: {first_result.index.size}")
    print(f"  Initial source: {first_result.source}")
    print(f"  Second source: {second_result.source}")
    print(f"  Borough: {geography.borough_name}")
    print(f"  Census tract GEOID: {geography.census_tract_geoid}")
    print(f"  Census tract label: {geography.census_tract_label}")
    print(f"  NTA: {geography.nta_code} — {geography.nta_name}")
    print(f"  CDTA: {geography.cdta_code} — {geography.cdta_name}")


if __name__ == "__main__":
    asyncio.run(main())
