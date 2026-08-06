from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.provider import NWSProvider
from app.integrations.nyc311.client import NYC311Client
from app.integrations.nyc_boundaries.provider import (
    NYCBoundaryIndexProvider,
)
from app.services.geospatial_enrichment import (
    GeospatialEnrichmentRunResult,
    enrich_all_pending_incidents,
)
from app.services.nyc311_ingestion import (
    NYC311SyncResult,
    sync_nyc311,
)
from app.services.weather_enrichment import (
    WeatherEnrichmentRunResult,
    enrich_all_pending_weather_incidents,
)


@dataclass(frozen=True, slots=True)
class NYC311WorkflowResult:
    """Combined synchronization and enrichment result."""

    synchronization: NYC311SyncResult
    geospatial_enrichment: GeospatialEnrichmentRunResult
    weather_enrichment: WeatherEnrichmentRunResult


async def synchronize_and_enrich_nyc311(
    db: AsyncSession,
    nyc311_client: NYC311Client,
    boundary_provider: NYCBoundaryIndexProvider,
    weather_provider: NWSProvider,
    *,
    page_size: int | None = None,
    max_pages: int | None = None,
    run_started_at: datetime | None = None,
    geospatial_batch_size: int = 250,
    geospatial_max_batches: int = 20,
    weather_batch_size: int = 100,
    weather_max_batches: int = 20,
) -> NYC311WorkflowResult:
    """Synchronize NYC 311 and run all enrichment stages."""

    synchronization = await sync_nyc311(
        db,
        nyc311_client,
        page_size=page_size,
        max_pages=max_pages,
        run_started_at=run_started_at,
    )

    geospatial_enrichment = (
        await enrich_all_pending_incidents(
            db,
            boundary_provider,
            batch_size=geospatial_batch_size,
            max_batches=geospatial_max_batches,
            enriched_at=synchronization.window_ended_at,
        )
    )

    weather_enrichment = (
        await enrich_all_pending_weather_incidents(
            db,
            weather_provider,
            batch_size=weather_batch_size,
            max_batches=weather_max_batches,
            enriched_at=synchronization.window_ended_at,
        )
    )

    return NYC311WorkflowResult(
        synchronization=synchronization,
        geospatial_enrichment=geospatial_enrichment,
        weather_enrichment=weather_enrichment,
    )
