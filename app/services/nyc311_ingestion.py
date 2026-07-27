from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.nyc311.client import NYC311Client
from app.integrations.nyc311.mapper import map_nyc311_record
from app.repositories.incidents import IncidentRepository
from app.repositories.ingestion_checkpoints import (
    IngestionCheckpointRepository,
    normalize_utc,
)

NYC311_SOURCE = "nyc311"


@dataclass(frozen=True)
class NYC311IngestionResult:
    fetched: int
    accepted: int
    skipped_missing_coordinates: int
    upserted: int


@dataclass(frozen=True)
class NYC311SyncResult:
    pages_processed: int
    fetched: int
    accepted: int
    skipped_missing_coordinates: int
    upserted: int
    window_started_at: datetime
    window_ended_at: datetime
    checkpoint_created_at: datetime | None
    reached_page_limit: bool


async def ingest_nyc311_page(
    db: AsyncSession,
    client: NYC311Client,
    *,
    page_number: int = 1,
    page_size: int = 100,
    created_after: datetime | None = None,
    created_before: datetime | None = None,
) -> NYC311IngestionResult:
    """Fetch, transform, and persist one page of NYC 311 incidents."""

    records = await client.fetch_page(
        page_number=page_number,
        page_size=page_size,
        created_after=created_after,
        created_before=created_before,
        sort_direction="asc",
    )

    incident_rows: list[dict[str, Any]] = []
    skipped_missing_coordinates = 0

    for record in records:
        mapped_record = map_nyc311_record(record)

        if mapped_record is None:
            skipped_missing_coordinates += 1
            continue

        incident_rows.append(mapped_record)

    upserted = await IncidentRepository.upsert_many(
        db,
        incident_rows,
    )

    return NYC311IngestionResult(
        fetched=len(records),
        accepted=len(incident_rows),
        skipped_missing_coordinates=skipped_missing_coordinates,
        upserted=upserted,
    )


async def sync_nyc311(
    db: AsyncSession,
    client: NYC311Client,
    *,
    page_size: int | None = None,
    max_pages: int | None = None,
    run_started_at: datetime | None = None,
) -> NYC311SyncResult:
    """Incrementally synchronize multiple pages of NYC 311 records."""

    settings = get_settings()

    resolved_page_size = (
        page_size
        if page_size is not None
        else settings.nyc_311_page_size
    )
    resolved_max_pages = (
        max_pages
        if max_pages is not None
        else settings.nyc_311_max_pages_per_run
    )

    if resolved_page_size < 1:
        raise ValueError("page_size must be at least 1")

    if resolved_max_pages < 1:
        raise ValueError("max_pages must be at least 1")

    window_ended_at = normalize_utc(
        run_started_at or datetime.now(UTC)
    )

    checkpoint = await IngestionCheckpointRepository.get(
        db,
        NYC311_SOURCE,
    )

    if (
        checkpoint is not None
        and checkpoint.last_successful_created_at is not None
    ):
        window_started_at = normalize_utc(
            checkpoint.last_successful_created_at
        ) - timedelta(
            minutes=settings.nyc_311_cursor_overlap_minutes
        )
    else:
        window_started_at = window_ended_at - timedelta(
            hours=settings.nyc_311_initial_lookback_hours
        )

    await IngestionCheckpointRepository.mark_started(
        db,
        NYC311_SOURCE,
        started_at=window_ended_at,
    )

    pages_processed = 0
    total_fetched = 0
    total_accepted = 0
    total_skipped = 0
    total_upserted = 0
    latest_created_at: datetime | None = None
    reached_page_limit = False

    try:
        for page_number in range(
            1,
            resolved_max_pages + 1,
        ):
            records = await client.fetch_page(
                page_number=page_number,
                page_size=resolved_page_size,
                created_after=window_started_at,
                created_before=window_ended_at,
                sort_direction="asc",
            )

            if not records:
                break

            pages_processed += 1
            total_fetched += len(records)

            incident_rows: list[dict[str, Any]] = []

            for record in records:
                record_created_at = normalize_utc(
                    record.created_date
                )

                if (
                    latest_created_at is None
                    or record_created_at > latest_created_at
                ):
                    latest_created_at = record_created_at

                mapped_record = map_nyc311_record(record)

                if mapped_record is None:
                    total_skipped += 1
                    continue

                incident_rows.append(mapped_record)

            total_accepted += len(incident_rows)

            total_upserted += (
                await IncidentRepository.upsert_many(
                    db,
                    incident_rows,
                )
            )

            if len(records) < resolved_page_size:
                break

            if page_number == resolved_max_pages:
                reached_page_limit = True

        # Only advance the cursor when the API actually returned a record.
        # This prevents a delayed source from causing records to be skipped.
        next_checkpoint = latest_created_at

        await IngestionCheckpointRepository.mark_succeeded(
            db,
            NYC311_SOURCE,
            latest_created_at=next_checkpoint,
            records_fetched=total_fetched,
            records_upserted=total_upserted,
        )

        return NYC311SyncResult(
            pages_processed=pages_processed,
            fetched=total_fetched,
            accepted=total_accepted,
            skipped_missing_coordinates=total_skipped,
            upserted=total_upserted,
            window_started_at=window_started_at,
            window_ended_at=window_ended_at,
            checkpoint_created_at=next_checkpoint,
            reached_page_limit=reached_page_limit,
        )

    except Exception as exc:
        await db.rollback()

        await IngestionCheckpointRepository.mark_failed(
            db,
            NYC311_SOURCE,
            error=str(exc)[:4000],
        )

        raise