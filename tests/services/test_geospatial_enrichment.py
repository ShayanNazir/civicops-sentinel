from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.nyc_boundaries.index import (
    NYCGeography,
)
from app.integrations.nyc_boundaries.provider import (
    BoundaryIndexLoadResult,
    NYCBoundaryIndexProvider,
)
from app.models.incident import Incident
from app.repositories.incidents import IncidentRepository
from app.services.geospatial_enrichment import (
    enrich_pending_incidents,
)


def build_incident(
    external_id: str,
    *,
    latitude: str,
    longitude: str,
) -> Incident:
    return Incident(
        source="nyc311",
        external_id=external_id,
        description="Test street condition incident",
        latitude=Decimal(latitude),
        longitude=Decimal(longitude),
        media_urls=[],
        context_data={},
    )


def build_geography() -> NYCGeography:
    return NYCGeography(
        census_tract_geoid="36061011900",
        census_tract_code="011900",
        census_tract_label="119",
        borough_tract_code="1011900",
        borough_code="1",
        borough_name="Manhattan",
        nta_code="MN0502",
        nta_name="Midtown-Times Square",
        cdta_code="MN05",
        cdta_name=("Midtown-Flatiron-Union Square (CD 5 Approximation)"),
    )


def build_db() -> MagicMock:
    db = MagicMock(spec=AsyncSession)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_enrichment_matches_and_marks_unmatched(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()

    matched_incident = build_incident(
        "1001",
        latitude="40.758000",
        longitude="-73.985500",
    )
    unmatched_incident = build_incident(
        "1002",
        latitude="27.950600",
        longitude="-82.457200",
    )

    geography = build_geography()

    index = MagicMock()
    index.resolve.side_effect = [
        geography,
        None,
    ]

    provider = MagicMock(spec=NYCBoundaryIndexProvider)
    provider.get_index = AsyncMock(
        return_value=BoundaryIndexLoadResult(
            index=index,
            source="redis",
        )
    )

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_geospatial",
        AsyncMock(
            return_value=[
                matched_incident,
                unmatched_incident,
            ]
        ),
    )

    enriched_at = datetime(
        2026,
        7,
        27,
        6,
        0,
        tzinfo=UTC,
    )

    result = await enrich_pending_incidents(
        db,
        provider,
        limit=100,
        enriched_at=enriched_at,
    )

    assert result.selected == 2
    assert result.matched == 1
    assert result.unmatched == 1
    assert result.index_source == "redis"

    assert matched_incident.geospatial_status == "matched"
    assert matched_incident.census_tract_geoid == "36061011900"
    assert matched_incident.borough_name == "Manhattan"
    assert matched_incident.nta_code == "MN0502"
    assert matched_incident.cdta_code == "MN05"
    assert matched_incident.geospatial_enriched_at == enriched_at

    assert unmatched_incident.geospatial_status == "unmatched"
    assert unmatched_incident.census_tract_geoid is None
    assert unmatched_incident.nta_code is None
    assert unmatched_incident.geospatial_enriched_at == enriched_at

    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrichment_handles_empty_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()

    index = MagicMock()

    provider = MagicMock(spec=NYCBoundaryIndexProvider)
    provider.get_index = AsyncMock(
        return_value=BoundaryIndexLoadResult(
            index=index,
            source="memory",
        )
    )

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_geospatial",
        AsyncMock(return_value=[]),
    )

    result = await enrich_pending_incidents(
        db,
        provider,
    )

    assert result.selected == 0
    assert result.matched == 0
    assert result.unmatched == 0
    assert result.index_source == "memory"

    index.resolve.assert_not_called()
    db.commit.assert_not_awaited()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrichment_rolls_back_commit_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = build_db()
    db.commit.side_effect = RuntimeError("Database commit failed")

    incident = build_incident(
        "1003",
        latitude="40.758000",
        longitude="-73.985500",
    )

    index = MagicMock()
    index.resolve.return_value = build_geography()

    provider = MagicMock(spec=NYCBoundaryIndexProvider)
    provider.get_index = AsyncMock(
        return_value=BoundaryIndexLoadResult(
            index=index,
            source="network",
        )
    )

    monkeypatch.setattr(
        IncidentRepository,
        "list_pending_geospatial",
        AsyncMock(return_value=[incident]),
    )

    with pytest.raises(
        RuntimeError,
        match="Database commit failed",
    ):
        await enrich_pending_incidents(
            db,
            provider,
        )

    db.rollback.assert_awaited_once()
