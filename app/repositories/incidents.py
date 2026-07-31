from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc_boundaries.index import NYCGeography
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


class IncidentRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        payload: IncidentCreate,
    ) -> Incident:
        incident = Incident(**payload.model_dump())
        db.add(incident)

        await db.commit()
        await db.refresh(incident)

        return incident

    @staticmethod
    async def get(
        db: AsyncSession,
        incident_id: UUID,
    ) -> Incident | None:
        return await db.get(Incident, incident_id)

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> list[Incident]:
        result = await db.execute(
            select(Incident).order_by(Incident.created_at.desc()).limit(limit).offset(offset)
        )

        return list(result.scalars().all())

    @staticmethod
    async def upsert_many(
        db: AsyncSession,
        rows: Sequence[dict[str, Any]],
    ) -> int:
        """
        Insert new incidents or update existing incidents.

        The database uniqueness constraint on source and external_id
        prevents repeated ingestion from creating duplicate records.
        """

        if not rows:
            return 0

        insert_statement = insert(Incident).values(list(rows))

        upsert_statement = insert_statement.on_conflict_do_update(
            constraint="uq_incident_source_external_id",
            set_={
                "description": insert_statement.excluded.description,
                "latitude": insert_statement.excluded.latitude,
                "longitude": insert_statement.excluded.longitude,
                "media_urls": insert_statement.excluded.media_urls,
                "status": insert_statement.excluded.status,
                "priority": insert_statement.excluded.priority,
                "context_data": insert_statement.excluded.context_data,
                "updated_at": func.now(),
            },
        )

        await db.execute(upsert_statement)
        await db.commit()

        return len(rows)

    @staticmethod
    async def list_pending_geospatial(
        db: AsyncSession,
        *,
        limit: int,
    ) -> list[Incident]:
        """
        Select pending incidents for geospatial enrichment.

        Locked rows are skipped so multiple workers can safely process
        separate batches without selecting the same incidents.
        """

        if limit < 1:
            raise ValueError("limit must be at least 1")

        result = await db.execute(
            select(Incident)
            .where(Incident.geospatial_status == "pending")
            .order_by(
                Incident.created_at.asc(),
                Incident.id.asc(),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )

        return list(result.scalars().all())

    @staticmethod
    async def save_geospatial_results(
        db: AsyncSession,
        resolutions: Sequence[tuple[Incident, NYCGeography | None]],
        *,
        enriched_at: datetime,
    ) -> None:
        """Save matched or unmatched geography for a batch."""

        for incident, geography in resolutions:
            incident.geospatial_enriched_at = enriched_at

            if geography is None:
                incident.geospatial_status = "unmatched"
                incident.census_tract_geoid = None
                incident.census_tract_code = None
                incident.census_tract_label = None
                incident.borough_tract_code = None
                incident.borough_code = None
                incident.borough_name = None
                incident.nta_code = None
                incident.nta_name = None
                incident.cdta_code = None
                incident.cdta_name = None
                continue

            incident.geospatial_status = "matched"
            incident.census_tract_geoid = geography.census_tract_geoid
            incident.census_tract_code = geography.census_tract_code
            incident.census_tract_label = geography.census_tract_label
            incident.borough_tract_code = geography.borough_tract_code
            incident.borough_code = geography.borough_code
            incident.borough_name = geography.borough_name
            incident.nta_code = geography.nta_code
            incident.nta_name = geography.nta_name
            incident.cdta_code = geography.cdta_code
            incident.cdta_name = geography.cdta_name

        await db.commit()
