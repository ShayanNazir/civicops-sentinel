from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc311.client import NYC311Client
from app.integrations.nyc311.schemas import NYC311Record
from app.models.ingestion_checkpoint import IngestionCheckpoint
from app.repositories.incidents import IncidentRepository
from app.repositories.ingestion_checkpoints import (
    IngestionCheckpointRepository,
)
from app.services import nyc311_ingestion as ingestion_module
from app.services.nyc311_ingestion import sync_nyc311


def build_record(
    unique_key: str,
    created_at: datetime,
) -> NYC311Record:
    """Create a valid NYC 311 record for synchronization tests."""

    return NYC311Record(
        unique_key=unique_key,
        created_date=created_at,
        agency="DOT",
        complaint_type="Street Condition",
        descriptor="Pothole",
        borough="BROOKLYN",
        latitude="40.712800",
        longitude="-74.006000",
    )


def build_mock_session() -> MagicMock:
    """Create a mocked asynchronous database session."""

    db = MagicMock(spec=AsyncSession)
    db.rollback = AsyncMock()

    return db


def patch_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Replace application settings with predictable test values."""

    settings = SimpleNamespace(
        nyc_311_page_size=2,
        nyc_311_max_pages_per_run=5,
        nyc_311_initial_lookback_hours=72,
        nyc_311_cursor_overlap_minutes=5,
    )

    monkeypatch.setattr(
        ingestion_module,
        "get_settings",
        lambda: settings,
    )


@pytest.mark.asyncio
async def test_sync_processes_multiple_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    db = build_mock_session()

    run_started_at = datetime(
        2026,
        7,
        25,
        16,
        0,
        tzinfo=UTC,
    )

    first_record = build_record(
        "1001",
        run_started_at - timedelta(hours=2),
    )
    second_record = build_record(
        "1002",
        run_started_at - timedelta(hours=1),
    )
    third_record = build_record(
        "1003",
        run_started_at - timedelta(minutes=30),
    )

    client = MagicMock(spec=NYC311Client)
    client.fetch_page = AsyncMock(
        side_effect=[
            [first_record, second_record],
            [third_record],
        ]
    )

    mark_started = AsyncMock()
    mark_succeeded = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "get",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_started",
        mark_started,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_succeeded",
        mark_succeeded,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_failed",
        mark_failed,
    )
    monkeypatch.setattr(
        IncidentRepository,
        "upsert_many",
        AsyncMock(side_effect=[2, 1]),
    )

    result = await sync_nyc311(
        db,
        client,
        page_size=2,
        max_pages=5,
        run_started_at=run_started_at,
    )

    expected_checkpoint = third_record.created_date

    assert result.pages_processed == 2
    assert result.fetched == 3
    assert result.accepted == 3
    assert result.skipped_missing_coordinates == 0
    assert result.upserted == 3
    assert result.reached_page_limit is False

    assert result.window_started_at == (
        run_started_at - timedelta(hours=72)
    )
    assert result.window_ended_at == run_started_at
    assert result.checkpoint_created_at == expected_checkpoint

    assert client.fetch_page.await_count == 2

    first_call = client.fetch_page.await_args_list[0]
    assert first_call.kwargs["page_number"] == 1
    assert first_call.kwargs["page_size"] == 2
    assert first_call.kwargs["sort_direction"] == "asc"
    assert first_call.kwargs["created_after"] == (
        run_started_at - timedelta(hours=72)
    )
    assert first_call.kwargs["created_before"] == run_started_at

    second_call = client.fetch_page.await_args_list[1]
    assert second_call.kwargs["page_number"] == 2
    assert second_call.kwargs["sort_direction"] == "asc"

    mark_started.assert_awaited_once_with(
        db,
        "nyc311",
        started_at=run_started_at,
    )

    mark_succeeded.assert_awaited_once_with(
        db,
        "nyc311",
        latest_created_at=expected_checkpoint,
        records_fetched=3,
        records_upserted=3,
    )

    mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_uses_existing_checkpoint_and_page_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    db = build_mock_session()

    run_started_at = datetime(
        2026,
        7,
        25,
        18,
        0,
        tzinfo=UTC,
    )
    existing_cursor = datetime(
        2026,
        7,
        25,
        17,
        0,
        tzinfo=UTC,
    )

    checkpoint = IngestionCheckpoint(
        source="nyc311",
        last_successful_created_at=existing_cursor,
    )

    first_record = build_record(
        "2001",
        datetime(
            2026,
            7,
            25,
            17,
            10,
            tzinfo=UTC,
        ),
    )
    second_record = build_record(
        "2002",
        datetime(
            2026,
            7,
            25,
            17,
            20,
            tzinfo=UTC,
        ),
    )

    client = MagicMock(spec=NYC311Client)
    client.fetch_page = AsyncMock(
        return_value=[
            first_record,
            second_record,
        ]
    )

    mark_started = AsyncMock()
    mark_succeeded = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "get",
        AsyncMock(return_value=checkpoint),
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_started",
        mark_started,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_succeeded",
        mark_succeeded,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_failed",
        mark_failed,
    )
    monkeypatch.setattr(
        IncidentRepository,
        "upsert_many",
        AsyncMock(return_value=2),
    )

    result = await sync_nyc311(
        db,
        client,
        page_size=2,
        max_pages=1,
        run_started_at=run_started_at,
    )

    expected_start = existing_cursor - timedelta(minutes=5)
    expected_checkpoint = second_record.created_date

    assert result.pages_processed == 1
    assert result.fetched == 2
    assert result.accepted == 2
    assert result.upserted == 2
    assert result.window_started_at == expected_start
    assert result.window_ended_at == run_started_at
    assert result.reached_page_limit is True
    assert result.checkpoint_created_at == expected_checkpoint

    fetch_call = client.fetch_page.await_args

    assert fetch_call.kwargs["page_number"] == 1
    assert fetch_call.kwargs["page_size"] == 2
    assert fetch_call.kwargs["created_after"] == expected_start
    assert fetch_call.kwargs["created_before"] == run_started_at
    assert fetch_call.kwargs["sort_direction"] == "asc"

    mark_succeeded.assert_awaited_once_with(
        db,
        "nyc311",
        latest_created_at=expected_checkpoint,
        records_fetched=2,
        records_upserted=2,
    )

    mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_does_not_advance_checkpoint_for_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    db = build_mock_session()

    run_started_at = datetime(
        2026,
        7,
        25,
        20,
        0,
        tzinfo=UTC,
    )

    client = MagicMock(spec=NYC311Client)
    client.fetch_page = AsyncMock(return_value=[])

    mark_started = AsyncMock()
    mark_succeeded = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "get",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_started",
        mark_started,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_succeeded",
        mark_succeeded,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_failed",
        mark_failed,
    )

    result = await sync_nyc311(
        db,
        client,
        page_size=2,
        max_pages=5,
        run_started_at=run_started_at,
    )

    assert result.pages_processed == 0
    assert result.fetched == 0
    assert result.accepted == 0
    assert result.skipped_missing_coordinates == 0
    assert result.upserted == 0
    assert result.checkpoint_created_at is None
    assert result.reached_page_limit is False

    mark_started.assert_awaited_once_with(
        db,
        "nyc311",
        started_at=run_started_at,
    )

    mark_succeeded.assert_awaited_once_with(
        db,
        "nyc311",
        latest_created_at=None,
        records_fetched=0,
        records_upserted=0,
    )

    mark_failed.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_records_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    db = build_mock_session()

    run_started_at = datetime(
        2026,
        7,
        25,
        19,
        0,
        tzinfo=UTC,
    )

    client = MagicMock(spec=NYC311Client)
    client.fetch_page = AsyncMock(
        side_effect=RuntimeError(
            "Temporary synchronization failure"
        )
    )

    mark_started = AsyncMock()
    mark_succeeded = AsyncMock()
    mark_failed = AsyncMock()

    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "get",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_started",
        mark_started,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_succeeded",
        mark_succeeded,
    )
    monkeypatch.setattr(
        IngestionCheckpointRepository,
        "mark_failed",
        mark_failed,
    )

    with pytest.raises(
        RuntimeError,
        match="Temporary synchronization failure",
    ):
        await sync_nyc311(
            db,
            client,
            page_size=2,
            max_pages=5,
            run_started_at=run_started_at,
        )

    db.rollback.assert_awaited_once()

    mark_started.assert_awaited_once_with(
        db,
        "nyc311",
        started_at=run_started_at,
    )

    mark_failed.assert_awaited_once_with(
        db,
        "nyc311",
        error="Temporary synchronization failure",
    )

    mark_succeeded.assert_not_awaited()