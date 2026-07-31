from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.integrations.nyc_boundaries.cache import (
    NYCBoundaryCache,
)
from app.integrations.nyc_boundaries.client import (
    NYCBoundaryClient,
)
from app.integrations.nyc_boundaries.provider import (
    NYCBoundaryIndexProvider,
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
                "ntaname": ("Financial District-Battery Park City"),
                "cdta2020": "MN01",
                "cdtaname": ("Manhattan Community District 1"),
            },
        }
    ],
}


def build_settings() -> Settings:
    return Settings(
        redis_url="redis://redis:6379/0",
        nyc_2020_census_tracts_dataset_id=("63ge-mke6"),
        nyc_boundary_cache_ttl_seconds=3600,
    )


def build_collection() -> CensusTractFeatureCollection:
    return CensusTractFeatureCollection.model_validate(SAMPLE_FEATURE_COLLECTION)


@pytest.mark.asyncio
async def test_cache_returns_valid_collection() -> None:
    collection = build_collection()

    redis_client = AsyncMock()
    redis_client.get.return_value = collection.model_dump_json()

    cache = NYCBoundaryCache(
        settings=build_settings(),
        client=redis_client,
    )

    result = await cache.get_feature_collection()

    assert result is not None
    assert len(result.features) == 1
    assert result.features[0].properties.boroname == "Manhattan"

    redis_client.get.assert_awaited_once_with(cache.cache_key)


@pytest.mark.asyncio
async def test_cache_removes_corrupted_value() -> None:
    redis_client = AsyncMock()
    redis_client.get.return_value = "this is not valid JSON"

    cache = NYCBoundaryCache(
        settings=build_settings(),
        client=redis_client,
    )

    result = await cache.get_feature_collection()

    assert result is None

    redis_client.delete.assert_awaited_once_with(cache.cache_key)


@pytest.mark.asyncio
async def test_provider_uses_network_then_memory() -> None:
    collection = build_collection()

    boundary_client = MagicMock(spec=NYCBoundaryClient)
    boundary_client.fetch_feature_collection = AsyncMock(return_value=collection)

    boundary_cache = MagicMock(spec=NYCBoundaryCache)
    boundary_cache.get_feature_collection = AsyncMock(return_value=None)
    boundary_cache.set_feature_collection = AsyncMock(return_value=True)

    provider = NYCBoundaryIndexProvider(
        client=boundary_client,
        cache=boundary_cache,
        settings=build_settings(),
    )

    first_result = await provider.get_index()
    second_result = await provider.get_index()

    assert first_result.source == "network"
    assert second_result.source == "memory"
    assert first_result.index is second_result.index

    boundary_client.fetch_feature_collection.assert_awaited_once()

    boundary_cache.set_feature_collection.assert_awaited_once_with(collection)


@pytest.mark.asyncio
async def test_provider_uses_redis_cache() -> None:
    collection = build_collection()

    boundary_client = MagicMock(spec=NYCBoundaryClient)
    boundary_client.fetch_feature_collection = AsyncMock()

    boundary_cache = MagicMock(spec=NYCBoundaryCache)
    boundary_cache.get_feature_collection = AsyncMock(return_value=collection)
    boundary_cache.set_feature_collection = AsyncMock()

    provider = NYCBoundaryIndexProvider(
        client=boundary_client,
        cache=boundary_cache,
        settings=build_settings(),
    )

    result = await provider.get_index()

    assert result.source == "redis"
    assert result.index.size == 1

    geography = result.index.resolve(
        latitude=40.75,
        longitude=-73.98,
    )

    assert geography is not None
    assert geography.borough_name == "Manhattan"

    boundary_client.fetch_feature_collection.assert_not_awaited()
    boundary_cache.set_feature_collection.assert_not_awaited()
