from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident
from app.repositories.incidents import IncidentRepository


def build_incident(
    external_id: str,
) -> Incident:
    return Incident(
        source="test",
        external_id=external_id,
        description="Spatial repository test",
        latitude=Decimal("40.758000"),
        longitude=Decimal("-73.985500"),
        media_urls=[],
        context_data={},
    )


@pytest.mark.asyncio
async def test_find_within_radius_returns_distance_ordered_results() -> None:
    first = build_incident("near-1")
    second = build_incident("near-2")

    result = MagicMock()
    result.all.return_value = [
        (first, 125.25),
        (second, 480.75),
    ]

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=result)

    nearby = await IncidentRepository.find_within_radius(
        db,
        latitude=40.7580,
        longitude=-73.9855,
        radius_meters=1_000,
        limit=10,
    )

    assert len(nearby) == 2

    assert nearby[0].incident is first
    assert nearby[0].distance_meters == 125.25

    assert nearby[1].incident is second
    assert nearby[1].distance_meters == 480.75

    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_within_radius_returns_empty_list() -> None:
    result = MagicMock()
    result.all.return_value = []

    db = MagicMock(spec=AsyncSession)
    db.execute = AsyncMock(return_value=result)

    nearby = await IncidentRepository.find_within_radius(
        db,
        latitude=40.7580,
        longitude=-73.9855,
        radius_meters=500,
    )

    assert nearby == []


@pytest.mark.asyncio
async def test_find_within_radius_rejects_invalid_radius() -> None:
    db = MagicMock(spec=AsyncSession)

    with pytest.raises(
        ValueError,
        match="radius_meters must be greater than 0",
    ):
        await IncidentRepository.find_within_radius(
            db,
            latitude=40.7580,
            longitude=-73.9855,
            radius_meters=0,
        )


@pytest.mark.asyncio
async def test_find_within_radius_rejects_invalid_coordinates() -> None:
    db = MagicMock(spec=AsyncSession)

    with pytest.raises(
        ValueError,
        match="latitude must be between -90 and 90",
    ):
        await IncidentRepository.find_within_radius(
            db,
            latitude=100,
            longitude=-73.9855,
            radius_meters=500,
        )
