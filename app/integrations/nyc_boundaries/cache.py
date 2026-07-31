import json

from pydantic import ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.integrations.nyc_boundaries.schemas import (
    CensusTractFeatureCollection,
)

BOUNDARY_CACHE_KEY_PREFIX = "civicops:nyc-boundaries"


class NYCBoundaryCache:
    """Redis-backed cache for validated NYC boundary GeoJSON."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: Redis | None = None,
    ) -> None:
        self.settings = settings or get_settings()

        self._owns_client = client is None
        self._client = client or Redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
        )

    @property
    def cache_key(self) -> str:
        """Return a versioned cache key for the configured dataset."""

        dataset_id = self.settings.nyc_2020_census_tracts_dataset_id

        return f"{BOUNDARY_CACHE_KEY_PREFIX}:{dataset_id}:feature-collection:v1"

    async def get_feature_collection(
        self,
    ) -> CensusTractFeatureCollection | None:
        """Return validated boundary data from Redis when available."""

        try:
            raw_value = await self._client.get(self.cache_key)
        except RedisError:
            # Boundary retrieval must still work when Redis is unavailable.
            return None

        if raw_value is None:
            return None

        try:
            payload = json.loads(raw_value)

            feature_collection = CensusTractFeatureCollection.model_validate(payload)
        except (
            json.JSONDecodeError,
            TypeError,
            ValidationError,
        ):
            # Remove corrupted or outdated cached data.
            try:
                await self._client.delete(self.cache_key)
            except RedisError:
                pass

            return None

        if not feature_collection.features:
            try:
                await self._client.delete(self.cache_key)
            except RedisError:
                pass

            return None

        return feature_collection

    async def set_feature_collection(
        self,
        feature_collection: CensusTractFeatureCollection,
    ) -> bool:
        """Store boundary data using the configured expiration time."""

        ttl_seconds = self.settings.nyc_boundary_cache_ttl_seconds

        if ttl_seconds < 1:
            raise ValueError("nyc_boundary_cache_ttl_seconds must be at least 1")

        try:
            await self._client.set(
                self.cache_key,
                feature_collection.model_dump_json(),
                ex=ttl_seconds,
            )
        except RedisError:
            # A cache failure should not fail the entire enrichment flow.
            return False

        return True

    async def clear(self) -> bool:
        """Remove the cached boundary dataset."""

        try:
            await self._client.delete(self.cache_key)
        except RedisError:
            return False

        return True

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(
        self,
    ) -> "NYCBoundaryCache":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()
