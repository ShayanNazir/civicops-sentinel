from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc_boundaries.provider import (
    BoundaryIndexSource,
    NYCBoundaryIndexProvider,
)
from app.repositories.incidents import IncidentRepository


@dataclass(frozen=True, slots=True)
class GeospatialEnrichmentResult:
    """Summary of one geospatial enrichment batch."""

    selected: int
    matched: int
    unmatched: int
    index_source: BoundaryIndexSource
    enriched_at: datetime


@dataclass(frozen=True, slots=True)
class GeospatialEnrichmentRunResult:
    """Summary of all enrichment batches in one workflow run."""

    batches_processed: int
    selected: int
    matched: int
    unmatched: int
    initial_index_source: BoundaryIndexSource
    reached_batch_limit: bool
    enriched_at: datetime


def normalize_enriched_at(
    value: datetime | None,
) -> datetime:
    """Return a timezone-aware UTC enrichment timestamp."""

    resolved_value = value or datetime.now(UTC)

    if resolved_value.tzinfo is None:
        return resolved_value.replace(tzinfo=UTC)

    return resolved_value.astimezone(UTC)


async def enrich_pending_incidents(
    db: AsyncSession,
    provider: NYCBoundaryIndexProvider,
    *,
    limit: int = 250,
    enriched_at: datetime | None = None,
) -> GeospatialEnrichmentResult:
    """Enrich one batch of pending incidents."""

    if not 1 <= limit <= 1_000:
        raise ValueError("limit must be between 1 and 1000")

    index_result = await provider.get_index()

    resolved_enriched_at = normalize_enriched_at(enriched_at)

    try:
        incidents = await IncidentRepository.list_pending_geospatial(
            db,
            limit=limit,
        )

        if not incidents:
            return GeospatialEnrichmentResult(
                selected=0,
                matched=0,
                unmatched=0,
                index_source=index_result.source,
                enriched_at=resolved_enriched_at,
            )

        resolutions = []
        matched = 0
        unmatched = 0

        for incident in incidents:
            geography = index_result.index.resolve(
                latitude=float(incident.latitude),
                longitude=float(incident.longitude),
            )

            resolutions.append(
                (
                    incident,
                    geography,
                )
            )

            if geography is None:
                unmatched += 1
            else:
                matched += 1

        await IncidentRepository.save_geospatial_results(
            db,
            resolutions,
            enriched_at=resolved_enriched_at,
        )

    except Exception:
        await db.rollback()
        raise

    return GeospatialEnrichmentResult(
        selected=len(incidents),
        matched=matched,
        unmatched=unmatched,
        index_source=index_result.source,
        enriched_at=resolved_enriched_at,
    )


async def enrich_all_pending_incidents(
    db: AsyncSession,
    provider: NYCBoundaryIndexProvider,
    *,
    batch_size: int = 250,
    max_batches: int = 20,
    enriched_at: datetime | None = None,
) -> GeospatialEnrichmentRunResult:
    """Process pending incidents in bounded batches."""

    if not 1 <= batch_size <= 1_000:
        raise ValueError("batch_size must be between 1 and 1000")

    if max_batches < 1:
        raise ValueError("max_batches must be at least 1")

    resolved_enriched_at = normalize_enriched_at(enriched_at)

    batches_processed = 0
    total_selected = 0
    total_matched = 0
    total_unmatched = 0
    reached_batch_limit = False

    initial_index_source: BoundaryIndexSource | None = None

    for batch_number in range(
        1,
        max_batches + 1,
    ):
        batch_result = await enrich_pending_incidents(
            db,
            provider,
            limit=batch_size,
            enriched_at=resolved_enriched_at,
        )

        if initial_index_source is None:
            initial_index_source = batch_result.index_source

        if batch_result.selected == 0:
            break

        batches_processed += 1
        total_selected += batch_result.selected
        total_matched += batch_result.matched
        total_unmatched += batch_result.unmatched

        if batch_result.selected < batch_size:
            break

        if batch_number == max_batches:
            reached_batch_limit = True

    assert initial_index_source is not None

    return GeospatialEnrichmentRunResult(
        batches_processed=batches_processed,
        selected=total_selected,
        matched=total_matched,
        unmatched=total_unmatched,
        initial_index_source=initial_index_source,
        reached_batch_limit=reached_batch_limit,
        enriched_at=resolved_enriched_at,
    )
