import asyncio

from app.db.session import AsyncSessionLocal
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
from app.services.geospatial_enrichment import (
    enrich_pending_incidents,
)


async def main() -> None:
    print("Starting incident geospatial enrichment...")

    try:
        async with AsyncSessionLocal() as db:
            async with NYCBoundaryClient() as client:
                async with NYCBoundaryCache() as cache:
                    provider = NYCBoundaryIndexProvider(
                        client=client,
                        cache=cache,
                    )

                    result = await enrich_pending_incidents(
                        db,
                        provider,
                    )

    except NYCBoundaryClientError as exc:
        print(f"Boundary request failed: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Geospatial enrichment failed: {exc}")
        raise

    print("Incident geospatial enrichment completed.")
    print(f"  Selected: {result.selected}")
    print(f"  Matched: {result.matched}")
    print(f"  Unmatched: {result.unmatched}")
    print(f"  Boundary index source: {result.index_source}")
    print(f"  Enriched at: {result.enriched_at.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
