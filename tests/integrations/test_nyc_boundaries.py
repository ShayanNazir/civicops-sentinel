import httpx
import pytest

from app.core.config import Settings
from app.integrations.nyc_boundaries.client import (
    NYCBoundaryClient,
    NYCBoundaryClientError,
)
from app.integrations.nyc_boundaries.index import (
    NYCBoundaryIndex,
)
from app.integrations.nyc_boundaries.schemas import (
    CensusTractFeatureCollection,
)

SAMPLE_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [-74.02, 40.70],
                        [-73.94, 40.70],
                        [-73.94, 40.80],
                        [-74.02, 40.80],
                        [-74.02, 40.70],
                    ]
                ],
            },
            "properties": {
                "geoid": "36061000100",
                "ct2020": "000100",
                "ctlabel": "1",
                "boroct2020": "1000100",
                "borocode": "1",
                "boroname": "Manhattan",
                "nta2020": "MN0101",
                "ntaname": "Financial District-Battery Park City",
                "cdta2020": "MN01",
                "cdtaname": "Manhattan Community District 1",
            },
        }
    ],
}


def build_settings() -> Settings:
    return Settings(
        nyc_open_data_base_url=("https://data.cityofnewyork.us"),
        nyc_2020_census_tracts_dataset_id="63ge-mke6",
        nyc_open_data_app_token="test-token",
    )


@pytest.mark.asyncio
async def test_client_fetches_and_indexes_boundaries() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.url.path == ("/resource/63ge-mke6.geojson")
        assert request.url.params["$limit"] == "5000"
        assert request.headers["X-App-Token"] == "test-token"

        return httpx.Response(
            200,
            json=SAMPLE_FEATURE_COLLECTION,
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NYCBoundaryClient(
            settings=build_settings(),
            client=http_client,
        )

        index = await client.fetch_index()

    assert index.size == 1

    geography = index.resolve(
        latitude=40.75,
        longitude=-73.98,
    )

    assert geography is not None
    assert geography.census_tract_geoid == "36061000100"
    assert geography.borough_name == "Manhattan"
    assert geography.nta_code == "MN0101"
    assert geography.cdta_code == "MN01"

    outside = index.resolve(
        latitude=41.0,
        longitude=-73.98,
    )

    assert outside is None


def test_index_rejects_invalid_coordinates() -> None:
    collection = CensusTractFeatureCollection.model_validate(SAMPLE_FEATURE_COLLECTION)
    index = NYCBoundaryIndex(collection.features)

    with pytest.raises(
        ValueError,
        match="latitude",
    ):
        index.resolve(
            latitude=100.0,
            longitude=-73.98,
        )

    with pytest.raises(
        ValueError,
        match="longitude",
    ):
        index.resolve(
            latitude=40.75,
            longitude=-200.0,
        )


@pytest.mark.asyncio
async def test_client_rejects_invalid_geojson() -> None:
    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "unexpected": "response",
            },
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NYCBoundaryClient(
            settings=build_settings(),
            client=http_client,
        )

        with pytest.raises(
            NYCBoundaryClientError,
            match="failed validation",
        ):
            await client.fetch_feature_collection()
