import asyncio

from app.db.session import AsyncSessionLocal
from app.integrations.nws.cache import NWSCache
from app.integrations.nws.client import (
    NWSClient,
    NWSClientError,
)
from app.integrations.nws.provider import NWSProvider
from app.integrations.nyc311.client import (
    NYC311Client,
    NYC311ClientError,
)
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
from app.services.nyc311_workflow import (
    synchronize_and_enrich_nyc311,
)


async def main() -> None:
    print("Starting NYC 311 synchronization, geospatial enrichment, and weather enrichment...")

    try:
        async with AsyncSessionLocal() as db:
            async with NYC311Client() as nyc311_client:
                async with NYCBoundaryClient() as boundary_client:
                    async with NYCBoundaryCache() as boundary_cache:
                        async with NWSClient() as nws_client:
                            async with NWSCache() as nws_cache:
                                boundary_provider = NYCBoundaryIndexProvider(
                                    client=boundary_client,
                                    cache=boundary_cache,
                                )

                                weather_provider = NWSProvider(
                                    client=nws_client,
                                    cache=nws_cache,
                                )

                                result = await synchronize_and_enrich_nyc311(
                                    db,
                                    nyc311_client,
                                    boundary_provider,
                                    weather_provider,
                                )

    except NYC311ClientError as exc:
        print(f"NYC 311 request failed: {exc}")
        raise SystemExit(1) from exc

    except NYCBoundaryClientError as exc:
        print(f"Boundary request failed: {exc}")
        raise SystemExit(1) from exc

    except NWSClientError as exc:
        print(f"NWS request failed: {exc}")
        raise SystemExit(1) from exc

    except Exception as exc:
        print(f"Workflow failed: {exc}")
        raise

    synchronization = result.synchronization
    geospatial = result.geospatial_enrichment
    weather = result.weather_enrichment

    print("NYC 311 synchronization completed.")
    print(f"  Pages processed: {synchronization.pages_processed}")
    print(f"  Records fetched: {synchronization.fetched}")
    print(f"  Records accepted: {synchronization.accepted}")
    print(f"  Missing coordinates: {synchronization.skipped_missing_coordinates}")
    print(f"  Records upserted: {synchronization.upserted}")
    print(
        "  Sync window: "
        f"{synchronization.window_started_at.isoformat()} "
        "to "
        f"{synchronization.window_ended_at.isoformat()}"
    )

    if synchronization.checkpoint_created_at is None:
        print("  New checkpoint: unchanged because no records were returned")
    else:
        print(f"  New checkpoint: {synchronization.checkpoint_created_at.isoformat()}")

    print(f"  Reached page limit: {synchronization.reached_page_limit}")

    print("Geospatial enrichment completed.")
    print(f"  Batches processed: {geospatial.batches_processed}")
    print(f"  Incidents selected: {geospatial.selected}")
    print(f"  Matched: {geospatial.matched}")
    print(f"  Unmatched: {geospatial.unmatched}")
    print(f"  Initial boundary source: {geospatial.initial_index_source}")
    print(f"  Reached batch limit: {geospatial.reached_batch_limit}")

    print("Weather enrichment completed.")
    print(f"  Batches processed: {weather.batches_processed}")
    print(f"  Incidents selected: {weather.selected}")
    print(f"  Matched: {weather.matched}")
    print(f"  Unavailable: {weather.unavailable}")
    print(f"  Reached batch limit: {weather.reached_batch_limit}")


if __name__ == "__main__":
    asyncio.run(main())
