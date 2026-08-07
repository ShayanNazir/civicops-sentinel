from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, call

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.provider import NWSProvider
from app.services import (
    weather_enrichment as weather_module,
)
from app.services.weather_enrichment import (
    WeatherEnrichmentResult,
)


@pytest.mark.asyncio
async def test_enrich_all_weather_processes_multiple_batches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    provider = MagicMock(spec=NWSProvider)

    enriched_at = datetime(
        2026,
        8,
        6,
        18,
        30,
        tzinfo=UTC,
    )

    enrich_batch = AsyncMock(
        side_effect=[
            WeatherEnrichmentResult(
                selected=2,
                matched=1,
                unavailable=1,
                enriched_at=enriched_at,
            ),
            WeatherEnrichmentResult(
                selected=1,
                matched=1,
                unavailable=0,
                enriched_at=enriched_at,
            ),
        ]
    )

    monkeypatch.setattr(
        weather_module,
        "enrich_pending_weather_incidents",
        enrich_batch,
    )

    result = (
        await weather_module
        .enrich_all_pending_weather_incidents(
            db,
            provider,
            batch_size=2,
            max_batches=5,
            enriched_at=enriched_at,
        )
    )

    assert result.batches_processed == 2
    assert result.selected == 3
    assert result.matched == 2
    assert result.unavailable == 1
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
async def test_enrich_all_weather_reports_batch_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = MagicMock(spec=AsyncSession)
    provider = MagicMock(spec=NWSProvider)

    enriched_at = datetime(
        2026,
        8,
        6,
        19,
        0,
        tzinfo=UTC,
    )

    full_batch = WeatherEnrichmentResult(
        selected=2,
        matched=2,
        unavailable=0,
        enriched_at=enriched_at,
    )

    enrich_batch = AsyncMock(
        side_effect=[
            full_batch,
            full_batch,
        ]
    )

    monkeypatch.setattr(
        weather_module,
        "enrich_pending_weather_incidents",
        enrich_batch,
    )

    result = (
        await weather_module
        .enrich_all_pending_weather_incidents(
            db,
            provider,
            batch_size=2,
            max_batches=2,
            enriched_at=enriched_at,
        )
    )

    assert result.batches_processed == 2
    assert result.selected == 4
    assert result.matched == 4
    assert result.unavailable == 0
    assert result.reached_batch_limit is True
    assert enrich_batch.await_count == 2