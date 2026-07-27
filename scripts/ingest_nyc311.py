import asyncio

from app.db.session import AsyncSessionLocal
from app.integrations.nyc311.client import (
    NYC311Client,
    NYC311ClientError,
)
from app.services.nyc311_ingestion import sync_nyc311


async def main() -> None:
    print("Starting incremental NYC 311 synchronization...")

    try:
        async with AsyncSessionLocal() as db:
            async with NYC311Client() as client:
                result = await sync_nyc311(
                    db,
                    client,
                )
    except NYC311ClientError as exc:
        print(f"NYC 311 request failed: {exc}")
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Synchronization failed: {exc}")
        raise

    print("NYC 311 synchronization completed.")
    print(f"  Pages processed: {result.pages_processed}")
    print(f"  Records fetched: {result.fetched}")
    print(f"  Records accepted: {result.accepted}")
    print(
        "  Missing coordinates: "
        f"{result.skipped_missing_coordinates}"
    )
    print(f"  Records upserted: {result.upserted}")
    print(
        "  Sync window: "
        f"{result.window_started_at.isoformat()} "
        f"to {result.window_ended_at.isoformat()}"
    )

    if result.checkpoint_created_at is None:
        print(
            "  New checkpoint: unchanged because "
            "no records were returned"
        )
    else:
        print(
            "  New checkpoint: "
            f"{result.checkpoint_created_at.isoformat()}"
        )

    print(
        "  Reached page limit: "
        f"{result.reached_page_limit}"
    )


if __name__ == "__main__":
    asyncio.run(main())