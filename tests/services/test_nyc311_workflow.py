from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.provider import NWSProvider
from app.integrations.nyc311.client import NYC311Client
from app.integrations.nyc_boundaries.provider import (
    NYCBoundaryIndexProvider,
)
from app.services import nyc311_workflow as workflow_module
from app.services.geospatial_enrichment import (
    GeospatialEnrichmentRunResult,
)
from app.services.nyc311_ingestion import (
    NYC311SyncResult,
)
from app.services.weather_enrichment import (
    WeatherEnrichmentRunResult,
)


def build_sync_result(
    run_started_at: datetime,
) -> NYC311SyncResult:
    return NYC311SyncResult(
        pages_processed=1,
        fetched=2,
        accepted=2,
        skipped_missing_coordinates=0,
        upserted=2,
        window_started_at=run_started_at,
        window_ended_at=run_started_at,
        checkpoint_created_at=run_started_at,
        reached_page_limit=False,
    )


def build_geospatial_result(
    enriched_at: datetime,
) -> GeospatialEnrichmentRunResult:
    return GeospatialEnrichmentRunResult(
        batches_processed=1,
        selected=2,
        matched=2,
        unmatched=0,
        initial_index_source="redis",
        reached_batch_limit=False,
        enriched_at=enriched_at,
    )


def build_weather_result(
    enriched_at: datetime,
) -> WeatherEnrichmentRunResult:
    return WeatherEnrichmentRunResult(
        batches_processed=1,
        selected=2,
        matched=2,
        unavailable=0,
        reached_batch_limit=False,
        enriched_at=enriched_at,
    )


@pytest.mark.asyncio
async def test_workflow_runs_all_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    nyc311_client = MagicMock(spec=NYC311Client)
    boundary_provider = MagicMock(
        spec=NYCBoundaryIndexProvider
    )
    weather_provider = MagicMock(spec=NWSProvider)

    run_started_at = datetime(
        2026,
        8,
        6,
        20,
        0,
        tzinfo=UTC,
    )

    synchronization = build_sync_result(
        run_started_at
    )
    geospatial = build_geospatial_result(
        run_started_at
    )
    weather = build_weather_result(
        run_started_at
    )

    sync_mock = AsyncMock(
        return_value=synchronization
    )
    geospatial_mock = AsyncMock(
        return_value=geospatial
    )
    weather_mock = AsyncMock(
        return_value=weather
    )

    monkeypatch.setattr(
        workflow_module,
        "sync_nyc311",
        sync_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_incidents",
        geospatial_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_weather_incidents",
        weather_mock,
    )

    result = (
        await workflow_module
        .synchronize_and_enrich_nyc311(
            db,
            nyc311_client,
            boundary_provider,
            weather_provider,
            page_size=100,
            max_pages=5,
            run_started_at=run_started_at,
            geospatial_batch_size=200,
            geospatial_max_batches=10,
            weather_batch_size=50,
            weather_max_batches=8,
        )
    )

    assert result.synchronization is synchronization
    assert result.geospatial_enrichment is geospatial
    assert result.weather_enrichment is weather

    sync_mock.assert_awaited_once_with(
        db,
        nyc311_client,
        page_size=100,
        max_pages=5,
        run_started_at=run_started_at,
    )

    geospatial_mock.assert_awaited_once_with(
        db,
        boundary_provider,
        batch_size=200,
        max_batches=10,
        enriched_at=run_started_at,
    )

    weather_mock.assert_awaited_once_with(
        db,
        weather_provider,
        batch_size=50,
        max_batches=8,
        enriched_at=run_started_at,
    )


@pytest.mark.asyncio
async def test_workflow_stops_when_sync_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    nyc311_client = MagicMock(spec=NYC311Client)
    boundary_provider = MagicMock(
        spec=NYCBoundaryIndexProvider
    )
    weather_provider = MagicMock(spec=NWSProvider)

    sync_mock = AsyncMock(
        side_effect=RuntimeError(
            "Synchronization failed"
        )
    )
    geospatial_mock = AsyncMock()
    weather_mock = AsyncMock()

    monkeypatch.setattr(
        workflow_module,
        "sync_nyc311",
        sync_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_incidents",
        geospatial_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_weather_incidents",
        weather_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Synchronization failed",
    ):
        await (
            workflow_module
            .synchronize_and_enrich_nyc311(
                db,
                nyc311_client,
                boundary_provider,
                weather_provider,
            )
        )

    geospatial_mock.assert_not_awaited()
    weather_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_workflow_skips_weather_when_geospatial_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    nyc311_client = MagicMock(spec=NYC311Client)
    boundary_provider = MagicMock(
        spec=NYCBoundaryIndexProvider
    )
    weather_provider = MagicMock(spec=NWSProvider)

    run_started_at = datetime(
        2026,
        8,
        6,
        21,
        0,
        tzinfo=UTC,
    )

    monkeypatch.setattr(
        workflow_module,
        "sync_nyc311",
        AsyncMock(
            return_value=build_sync_result(
                run_started_at
            )
        ),
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_incidents",
        AsyncMock(
            side_effect=RuntimeError(
                "Geospatial enrichment failed"
            )
        ),
    )

    weather_mock = AsyncMock()

    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_weather_incidents",
        weather_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Geospatial enrichment failed",
    ):
        await (
            workflow_module
            .synchronize_and_enrich_nyc311(
                db,
                nyc311_client,
                boundary_provider,
                weather_provider,
            )
        )

    weather_mock.assert_not_awaited()