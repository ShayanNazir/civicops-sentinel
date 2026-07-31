from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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


@pytest.mark.asyncio
async def test_workflow_syncs_then_enriches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    nyc311_client = MagicMock(spec=NYC311Client)
    boundary_provider = MagicMock(spec=NYCBoundaryIndexProvider)

    run_started_at = datetime(
        2026,
        7,
        31,
        22,
        0,
        tzinfo=UTC,
    )

    synchronization = build_sync_result(run_started_at)

    enrichment = GeospatialEnrichmentRunResult(
        batches_processed=1,
        selected=2,
        matched=2,
        unmatched=0,
        initial_index_source="redis",
        reached_batch_limit=False,
        enriched_at=run_started_at,
    )

    sync_mock = AsyncMock(return_value=synchronization)
    enrich_mock = AsyncMock(return_value=enrichment)

    monkeypatch.setattr(
        workflow_module,
        "sync_nyc311",
        sync_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_incidents",
        enrich_mock,
    )

    result = await workflow_module.synchronize_and_enrich_nyc311(
        db,
        nyc311_client,
        boundary_provider,
        page_size=100,
        max_pages=5,
        run_started_at=run_started_at,
        enrichment_batch_size=200,
        enrichment_max_batches=10,
    )

    assert result.synchronization is synchronization
    assert result.enrichment is enrichment

    sync_mock.assert_awaited_once_with(
        db,
        nyc311_client,
        page_size=100,
        max_pages=5,
        run_started_at=run_started_at,
    )

    enrich_mock.assert_awaited_once_with(
        db,
        boundary_provider,
        batch_size=200,
        max_batches=10,
        enriched_at=run_started_at,
    )


@pytest.mark.asyncio
async def test_workflow_skips_enrichment_when_sync_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    nyc311_client = MagicMock(spec=NYC311Client)
    boundary_provider = MagicMock(spec=NYCBoundaryIndexProvider)

    sync_mock = AsyncMock(side_effect=RuntimeError("Synchronization failed"))
    enrich_mock = AsyncMock()

    monkeypatch.setattr(
        workflow_module,
        "sync_nyc311",
        sync_mock,
    )
    monkeypatch.setattr(
        workflow_module,
        "enrich_all_pending_incidents",
        enrich_mock,
    )

    with pytest.raises(
        RuntimeError,
        match="Synchronization failed",
    ):
        await workflow_module.synchronize_and_enrich_nyc311(
            db,
            nyc311_client,
            boundary_provider,
        )

    enrich_mock.assert_not_awaited()
