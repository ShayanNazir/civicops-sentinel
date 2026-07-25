from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion_checkpoint import IngestionCheckpoint


def normalize_utc(value: datetime) -> datetime:
    """Return an aware datetime normalized to UTC."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


class IngestionCheckpointRepository:
    """Persistence operations for external-data synchronization state."""

    @staticmethod
    async def get(
        db: AsyncSession,
        source: str,
    ) -> IngestionCheckpoint | None:
        return await db.get(IngestionCheckpoint, source)

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        source: str,
    ) -> IngestionCheckpoint:
        checkpoint = await db.get(IngestionCheckpoint, source)

        if checkpoint is None:
            checkpoint = IngestionCheckpoint(source=source)
            db.add(checkpoint)
            await db.flush()

        return checkpoint

    @classmethod
    async def mark_started(
        cls,
        db: AsyncSession,
        source: str,
        *,
        started_at: datetime | None = None,
    ) -> IngestionCheckpoint:
        checkpoint = await cls.get_or_create(db, source)

        checkpoint.last_run_started_at = normalize_utc(started_at or datetime.now(UTC))
        checkpoint.last_run_completed_at = None
        checkpoint.last_status = "running"
        checkpoint.last_error = None

        await db.commit()
        await db.refresh(checkpoint)

        return checkpoint

    @classmethod
    async def mark_succeeded(
        cls,
        db: AsyncSession,
        source: str,
        *,
        latest_created_at: datetime | None,
        records_fetched: int,
        records_upserted: int,
        completed_at: datetime | None = None,
    ) -> IngestionCheckpoint:
        checkpoint = await cls.get_or_create(db, source)

        if latest_created_at is not None:
            normalized_latest = normalize_utc(latest_created_at)

            if (
                checkpoint.last_successful_created_at is None
                or normalized_latest > checkpoint.last_successful_created_at
            ):
                checkpoint.last_successful_created_at = normalized_latest

        checkpoint.last_run_completed_at = normalize_utc(completed_at or datetime.now(UTC))
        checkpoint.last_status = "succeeded"
        checkpoint.last_error = None

        checkpoint.total_records_fetched = (checkpoint.total_records_fetched or 0) + records_fetched

        checkpoint.total_records_upserted = (
            checkpoint.total_records_upserted or 0
        ) + records_upserted

        await db.commit()
        await db.refresh(checkpoint)

        return checkpoint

    @classmethod
    async def mark_failed(
        cls,
        db: AsyncSession,
        source: str,
        *,
        error: str,
        completed_at: datetime | None = None,
    ) -> IngestionCheckpoint:
        checkpoint = await cls.get_or_create(db, source)

        checkpoint.last_run_completed_at = normalize_utc(completed_at or datetime.now(UTC))
        checkpoint.last_status = "failed"
        checkpoint.last_error = error

        await db.commit()
        await db.refresh(checkpoint)

        return checkpoint
