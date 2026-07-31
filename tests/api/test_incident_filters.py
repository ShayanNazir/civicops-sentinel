from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.main import app
from app.repositories.incidents import IncidentRepository

client = TestClient(app)


def build_incident() -> SimpleNamespace:
    timestamp = datetime(
        2026,
        7,
        31,
        18,
        0,
        tzinfo=UTC,
    )

    return SimpleNamespace(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        source="nyc311",
        external_id="12345678",
        description="Street condition: pothole",
        latitude=Decimal("40.758000"),
        longitude=Decimal("-73.985500"),
        media_urls=[],
        context_data={},
        status="received",
        priority="untriaged",
        geospatial_status="matched",
        geospatial_enriched_at=timestamp,
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
        created_at=timestamp,
        updated_at=timestamp,
    )


@pytest.mark.asyncio
async def test_list_incidents_forwards_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository_list = AsyncMock(return_value=[build_incident()])

    monkeypatch.setattr(
        IncidentRepository,
        "list",
        repository_list,
    )

    async def override_get_db():
        yield AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = override_get_db

    try:
        response = client.get(
            "/api/v1/incidents",
            params={
                "limit": 10,
                "offset": 5,
                "source": "nyc311",
                "borough": "Manhattan",
                "nta_code": "MN0502",
                "cdta_code": "MN05",
                "census_tract_geoid": ("36061011900"),
                "geospatial_status": "matched",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 1
    assert payload[0]["borough_name"] == "Manhattan"
    assert payload[0]["nta_code"] == "MN0502"
    assert payload[0]["cdta_code"] == "MN05"

    repository_list.assert_awaited_once()

    call = repository_list.await_args

    assert call.kwargs == {
        "limit": 10,
        "offset": 5,
        "source": "nyc311",
        "borough": "Manhattan",
        "nta_code": "MN0502",
        "cdta_code": "MN05",
        "census_tract_geoid": "36061011900",
        "geospatial_status": "matched",
    }


def test_list_incidents_rejects_invalid_status() -> None:
    response = client.get(
        "/api/v1/incidents",
        params={
            "geospatial_status": "finished",
        },
    )

    assert response.status_code == 422
