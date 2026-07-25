import asyncio

from app.db.session import AsyncSessionLocal
from app.integrations.nyc311.client import NYC311Client, NYC311ClientError
from app.services.nyc311_ingestion import ingest_nyc311_page


async def main() -> None:
    print("Starting NYC 311 ingestion...")

    try:
        async with AsyncSessionLocal() as db:
            async with NYC311Client() as client:
                result = await ingest_nyc311_page(
                    db,
                    client,
                    page_number=1,
                    page_size=25,
                )
    except NYC311ClientError as exc:
        print(f"Ingestion failed while calling NYC 311: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Ingestion failed unexpectedly: {exc}")
        raise

    print("NYC 311 ingestion completed.")
    print(f"  Records fetched: {result.fetched}")
    print(f"  Records accepted: {result.accepted}")
    print(f"  Missing coordinates: {result.skipped_missing_coordinates}")
    print(f"  Records upserted: {result.upserted}")


if __name__ == "__main__":
    asyncio.run(main())
