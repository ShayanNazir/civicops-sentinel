from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nws.client import NWSNotFoundError
from app.integrations.nws.provider import NWSProvider
from app.integrations.nws.resolver import (
    resolve_hourly_weather,
)
from app.repositories.incidents import IncidentRepository


@dataclass(frozen=True, slots=True)
class WeatherEnrichmentResult:
    """Summary of one weather enrichment batch."""

    selected: int
    matched: int
    unavailable: int
    enriched_at: datetime


@dataclass(frozen=True, slots=True)
class WeatherEnrichmentRunResult:
    """Summary of all weather batches in one run."""

    batches_processed: int
    selected: int
    matched: int
    unavailable: int
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


async def enrich_pending_weather_incidents(
    db: AsyncSession,
    provider: NWSProvider,
    *,
    limit: int = 100,
    enriched_at: datetime | None = None,
) -> WeatherEnrichmentResult:
    """Enrich one batch of pending incidents with NWS weather."""

    if not 1 <= limit <= 1_000:
        raise ValueError(
            "limit must be between 1 and 1000"
        )

    resolved_enriched_at = normalize_enriched_at(
        enriched_at
    )

    try:
        incidents = (
            await IncidentRepository.list_pending_weather(
                db,
                limit=limit,
            )
        )

        if not incidents:
            return WeatherEnrichmentResult(
                selected=0,
                matched=0,
                unavailable=0,
                enriched_at=resolved_enriched_at,
            )

        resolutions = []
        matched = 0
        unavailable = 0

        for incident in incidents:
            try:
                weather = await resolve_hourly_weather(
                    provider,
                    latitude=float(incident.latitude),
                    longitude=float(incident.longitude),
                    at=resolved_enriched_at,
                )
            except NWSNotFoundError:
                weather = None

            resolutions.append(
                (
                    incident,
                    weather,
                )
            )

            if weather is None:
                unavailable += 1
            else:
                matched += 1

        await IncidentRepository.save_weather_results(
            db,
            resolutions,
            enriched_at=resolved_enriched_at,
        )

    except Exception:
        await db.rollback()
        raise

    return WeatherEnrichmentResult(
        selected=len(incidents),
        matched=matched,
        unavailable=unavailable,
        enriched_at=resolved_enriched_at,
    )


async def enrich_all_pending_weather_incidents(
    db: AsyncSession,
    provider: NWSProvider,
    *,
    batch_size: int = 100,
    max_batches: int = 20,
    enriched_at: datetime | None = None,
) -> WeatherEnrichmentRunResult:
    """Process pending weather incidents in bounded batches."""

    if not 1 <= batch_size <= 1_000:
        raise ValueError(
            "batch_size must be between 1 and 1000"
        )

    if max_batches < 1:
        raise ValueError(
            "max_batches must be at least 1"
        )

    resolved_enriched_at = normalize_enriched_at(
        enriched_at
    )

    batches_processed = 0
    total_selected = 0
    total_matched = 0
    total_unavailable = 0
    reached_batch_limit = False

    for batch_number in range(
        1,
        max_batches + 1,
    ):
        batch_result = (
            await enrich_pending_weather_incidents(
                db,
                provider,
                limit=batch_size,
                enriched_at=resolved_enriched_at,
            )
        )

        if batch_result.selected == 0:
            break

        batches_processed += 1
        total_selected += batch_result.selected
        total_matched += batch_result.matched
        total_unavailable += batch_result.unavailable

        if batch_result.selected < batch_size:
            break

        if batch_number == max_batches:
            reached_batch_limit = True

    return WeatherEnrichmentRunResult(
        batches_processed=batches_processed,
        selected=total_selected,
        matched=total_matched,
        unavailable=total_unavailable,
        reached_batch_limit=reached_batch_limit,
        enriched_at=resolved_enriched_at,
    )