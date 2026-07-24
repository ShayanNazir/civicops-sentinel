from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.incidents import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentRead

router = APIRouter()


@router.post("", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
) -> IncidentRead:
    try:
        incident = await IncidentRepository.create(db, payload)
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An incident with this source and external ID already exists.",
        ) from exc

    return IncidentRead.model_validate(incident)


@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentRead]:
    incidents = await IncidentRepository.list(db, limit=limit, offset=offset)
    return [IncidentRead.model_validate(incident) for incident in incidents]


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentRead:
    incident = await IncidentRepository.get(db, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return IncidentRead.model_validate(incident)
