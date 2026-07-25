from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc311.client import NYC311Client
from app.integrations.nyc311.mapper import map_nyc311_record
from app.repositories.incidents import IncidentRepository


@dataclass(frozen=True)
class NYC311IngestionResult:
    fetched: int
    accepted: int
    skipped_missing_coordinates: int
    upserted: int


async def ingest_nyc311_page(
    db: AsyncSession,
    client: NYC311Client,
    *,
    page_number: int = 1,
    page_size: int = 100,
) -> NYC311IngestionResult:
    """Fetch, transform, and persist one page of NYC 311 incidents."""

    records = await client.fetch_page(
        page_number=page_number,
        page_size=page_size,
    )

    incident_rows = []
    skipped_missing_coordinates = 0

    for record in records:
        mapped_record = map_nyc311_record(record)

        if mapped_record is None:
            skipped_missing_coordinates += 1
            continue

        incident_rows.append(mapped_record)

    upserted = await IncidentRepository.upsert_many(
        db,
        incident_rows,
    )

    return NYC311IngestionResult(
        fetched=len(records),
        accepted=len(incident_rows),
        skipped_missing_coordinates=skipped_missing_coordinates,
        upserted=upserted,
    )
