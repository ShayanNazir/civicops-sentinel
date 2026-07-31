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

    resolved_enriched_at = enriched_at or datetime.now(UTC)

    if resolved_enriched_at.tzinfo is None:
        resolved_enriched_at = resolved_enriched_at.replace(tzinfo=UTC)
    else:
        resolved_enriched_at = resolved_enriched_at.astimezone(UTC)

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
