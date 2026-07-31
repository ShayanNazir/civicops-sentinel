from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc_boundaries.provider import (
    NYCBoundaryIndexProvider,
)
from app.services import (
    geospatial_enrichment as enrichment_module,
)
from app.services.geospatial_enrichment import (
    GeospatialEnrichmentResult,
)


@pytest.mark.asyncio
async def test_enrich_all_processes_multiple_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    provider = MagicMock(spec=NYCBoundaryIndexProvider)

    enriched_at = datetime(
        2026,
        7,
        31,
        20,
        0,
        tzinfo=UTC,
    )

    enrich_batch = AsyncMock(
        side_effect=[
            GeospatialEnrichmentResult(
                selected=2,
                matched=1,
                unmatched=1,
                index_source="redis",
                enriched_at=enriched_at,
            ),
            GeospatialEnrichmentResult(
                selected=1,
                matched=1,
                unmatched=0,
                index_source="memory",
                enriched_at=enriched_at,
            ),
        ]
    )

    monkeypatch.setattr(
        enrichment_module,
        "enrich_pending_incidents",
        enrich_batch,
    )

    result = await enrichment_module.enrich_all_pending_incidents(
        db,
        provider,
        batch_size=2,
        max_batches=5,
        enriched_at=enriched_at,
    )

    assert result.batches_processed == 2
    assert result.selected == 3
    assert result.matched == 2
    assert result.unmatched == 1
    assert result.initial_index_source == "redis"
    assert result.reached_batch_limit is False

    assert enrich_batch.await_args_list == [
        call(
            db,
            provider,
            limit=2,
            enriched_at=enriched_at,
        ),
        call(
            db,
            provider,
            limit=2,
            enriched_at=enriched_at,
        ),
    ]


@pytest.mark.asyncio
async def test_enrich_all_reports_batch_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    provider = MagicMock(spec=NYCBoundaryIndexProvider)

    enriched_at = datetime(
        2026,
        7,
        31,
        21,
        0,
        tzinfo=UTC,
    )

    full_batch = GeospatialEnrichmentResult(
        selected=2,
        matched=2,
        unmatched=0,
        index_source="memory",
        enriched_at=enriched_at,
    )

    enrich_batch = AsyncMock(
        side_effect=[
            full_batch,
            full_batch,
        ]
    )

    monkeypatch.setattr(
        enrichment_module,
        "enrich_pending_incidents",
        enrich_batch,
    )

    result = await enrichment_module.enrich_all_pending_incidents(
        db,
        provider,
        batch_size=2,
        max_batches=2,
        enriched_at=enriched_at,
    )

    assert result.batches_processed == 2
    assert result.selected == 4
    assert result.matched == 4
    assert result.unmatched == 0
    assert result.reached_batch_limit is True
    assert enrich_batch.await_count == 2
