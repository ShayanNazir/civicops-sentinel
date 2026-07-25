from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

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

        The database uniqueness constraint on source and external_id ensures
        repeated ingestion does not create duplicate records.
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
