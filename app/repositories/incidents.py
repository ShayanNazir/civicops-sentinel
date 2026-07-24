from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.schemas.incident import IncidentCreate


class IncidentRepository:
    @staticmethod
    async def create(db: AsyncSession, payload: IncidentCreate) -> Incident:
        incident = Incident(**payload.model_dump())
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def get(db: AsyncSession, incident_id: UUID) -> Incident | None:
        return await db.get(Incident, incident_id)

    @staticmethod
    async def list(
        db: AsyncSession,
        *,
        limit: int,
        offset: int,
    ) -> list[Incident]:
        result = await db.execute(
            select(Incident)
            .order_by(Incident.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
