from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ingestion_checkpoint import IngestionCheckpoint
from app.repositories.ingestion_checkpoints import (
    IngestionCheckpointRepository,
)


def build_mock_session(
    checkpoint: IngestionCheckpoint | None,
) -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.get = AsyncMock(return_value=checkpoint)
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_mark_started_creates_checkpoint() -> None:
    db = build_mock_session(None)
    started_at = datetime(2026, 7, 25, 5, 0, tzinfo=UTC)

    checkpoint = await IngestionCheckpointRepository.mark_started(
        db,
        "nyc311",
        started_at=started_at,
    )

    assert checkpoint.source == "nyc311"
    assert checkpoint.last_status == "running"
    assert checkpoint.last_run_started_at == started_at
    assert checkpoint.last_error is None

    db.add.assert_called_once_with(checkpoint)
    db.flush.assert_awaited_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(checkpoint)


@pytest.mark.asyncio
async def test_mark_succeeded_updates_cursor_and_totals() -> None:
    checkpoint = IngestionCheckpoint(
        source="nyc311",
        total_records_fetched=10,
        total_records_upserted=8,
    )
    db = build_mock_session(checkpoint)

    latest_created_at = datetime(
        2026,
        7,
        25,
        5,
        30,
        tzinfo=UTC,
    )
    completed_at = datetime(
        2026,
        7,
        25,
        5,
        35,
        tzinfo=UTC,
    )

    result = await IngestionCheckpointRepository.mark_succeeded(
        db,
        "nyc311",
        latest_created_at=latest_created_at,
        records_fetched=25,
        records_upserted=20,
        completed_at=completed_at,
    )

    assert result.last_status == "succeeded"
    assert result.last_successful_created_at == latest_created_at
    assert result.last_run_completed_at == completed_at
    assert result.total_records_fetched == 35
    assert result.total_records_upserted == 28

    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(checkpoint)
