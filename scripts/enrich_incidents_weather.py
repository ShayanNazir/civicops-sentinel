import asyncio

from app.db.session import AsyncSessionLocal
from app.integrations.nws.cache import NWSCache
from app.integrations.nws.client import (
    NWSClient,
    NWSClientError,
)
from app.integrations.nws.provider import NWSProvider
from app.services.weather_enrichment import (
    enrich_pending_weather_incidents,
)


async def main() -> None:
    print("Starting incident weather enrichment...")

    try:
        async with AsyncSessionLocal() as db:
            async with NWSClient() as client:
                async with NWSCache() as cache:
                    provider = NWSProvider(
                        client=client,
                        cache=cache,
                    )

                    result = await enrich_pending_weather_incidents(
                        db,
                        provider,
                    )

    except NWSClientError as exc:
        print(f"NWS request failed: {exc}")
        raise SystemExit(1) from exc

    except Exception as exc:
        print(f"Weather enrichment failed: {exc}")
        raise

    print("Incident weather enrichment completed.")
    print(f"  Selected: {result.selected}")
    print(f"  Matched: {result.matched}")
    print(f"  Unavailable: {result.unavailable}")
    print(f"  Enriched at: {result.enriched_at.isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
