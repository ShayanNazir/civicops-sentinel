from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.incidents import IncidentRepository
from app.schemas.incident import IncidentCreate, IncidentRead

router = APIRouter()

GeospatialStatus = Literal[
    "pending",
    "matched",
    "unmatched",
]

WeatherStatus = Literal[
    "pending",
    "matched",
    "unavailable",
]


@router.post(
    "",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    payload: IncidentCreate,
    db: AsyncSession = Depends(get_db),
) -> IncidentRead:
    try:
        incident = await IncidentRepository.create(
            db,
            payload,
        )
    except IntegrityError as exc:
        await db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=("An incident with this source and external ID already exists."),
        ) from exc

    return IncidentRead.model_validate(incident)


@router.get(
    "",
    response_model=list[IncidentRead],
)
async def list_incidents(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    source: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    borough: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),
    nta_code: str | None = Query(
        default=None,
        min_length=1,
        max_length=10,
    ),
    cdta_code: str | None = Query(
        default=None,
        min_length=1,
        max_length=10,
    ),
    census_tract_geoid: str | None = Query(
        default=None,
        min_length=1,
        max_length=11,
    ),
    geospatial_status: GeospatialStatus | None = Query(
        default=None,
    ),
    weather_status: WeatherStatus | None = Query(
        default=None,
    ),
    nws_office: str | None = Query(
        default=None,
        min_length=1,
        max_length=10,
    ),
    min_temperature: Decimal | None = Query(
        default=None,
        ge=-200,
        le=200,
    ),
    max_temperature: Decimal | None = Query(
        default=None,
        ge=-200,
        le=200,
    ),
    min_precipitation_probability: Decimal | None = Query(
        default=None,
        ge=0,
        le=100,
    ),
    max_precipitation_probability: Decimal | None = Query(
        default=None,
        ge=0,
        le=100,
    ),
    weather_condition: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
    ),
    weather_is_daytime: bool | None = Query(
        default=None,
    ),
    db: AsyncSession = Depends(get_db),
) -> list[IncidentRead]:
    if (
        min_temperature is not None
        and max_temperature is not None
        and min_temperature > max_temperature
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=("min_temperature cannot be greater than max_temperature."),
        )

    if (
        min_precipitation_probability is not None
        and max_precipitation_probability is not None
        and min_precipitation_probability > max_precipitation_probability
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "min_precipitation_probability cannot be "
                "greater than "
                "max_precipitation_probability."
            ),
        )

    incidents = await IncidentRepository.list(
        db,
        limit=limit,
        offset=offset,
        source=source,
        borough=borough,
        nta_code=nta_code,
        cdta_code=cdta_code,
        census_tract_geoid=census_tract_geoid,
        geospatial_status=geospatial_status,
        weather_status=weather_status,
        nws_office=nws_office,
        min_temperature=min_temperature,
        max_temperature=max_temperature,
        min_precipitation_probability=(min_precipitation_probability),
        max_precipitation_probability=(max_precipitation_probability),
        weather_condition=weather_condition,
        weather_is_daytime=weather_is_daytime,
    )

    return [IncidentRead.model_validate(incident) for incident in incidents]


@router.get(
    "/{incident_id}",
    response_model=IncidentRead,
)
async def get_incident(
    incident_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> IncidentRead:
    incident = await IncidentRepository.get(
        db,
        incident_id,
    )

    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found.",
        )

    return IncidentRead.model_validate(incident)
