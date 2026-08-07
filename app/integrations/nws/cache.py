import hashlib
import json
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import Settings, get_settings
from app.integrations.nws.schemas import (
    NWSHourlyForecastResponse,
    NWSPointResponse,
)

NWS_CACHE_KEY_PREFIX = "civicops:nws"

ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)


class NWSCache:
    """Redis-backed cache for validated NWS responses."""

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

    @staticmethod
    def point_cache_key(
        *,
        latitude: float,
        longitude: float,
    ) -> str:
        """Return a versioned point-metadata key."""

        return (
            f"{NWS_CACHE_KEY_PREFIX}:point:"
            f"{latitude:.4f}:{longitude:.4f}:v1"
        )

    @staticmethod
    def hourly_forecast_cache_key(
        forecast_url: str,
    ) -> str:
        """Return a stable key without embedding the full URL."""

        digest = hashlib.sha256(
            forecast_url.encode("utf-8")
        ).hexdigest()[:24]

        return (
            f"{NWS_CACHE_KEY_PREFIX}:"
            f"hourly-forecast:{digest}:v1"
        )

    async def _delete_invalid_value(
        self,
        key: str,
    ) -> None:
        try:
            await self._client.delete(key)
        except RedisError:
            pass

    async def _get_model(
        self,
        *,
        key: str,
        model_type: type[ModelT],
    ) -> ModelT | None:
        try:
            raw_value = await self._client.get(key)
        except RedisError:
            return None

        if raw_value is None:
            return None

        try:
            payload = json.loads(raw_value)
            return model_type.model_validate(payload)
        except (
            json.JSONDecodeError,
            TypeError,
            ValidationError,
        ):
            await self._delete_invalid_value(key)
            return None

    async def _set_model(
        self,
        *,
        key: str,
        value: BaseModel,
        ttl_seconds: int,
    ) -> bool:
        if ttl_seconds < 1:
            raise ValueError(
                "cache TTL must be at least 1 second"
            )

        try:
            await self._client.set(
                key,
                value.model_dump_json(
                    by_alias=True,
                ),
                ex=ttl_seconds,
            )
        except RedisError:
            return False

        return True

    async def get_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> NWSPointResponse | None:
        """Return cached NWS point metadata."""

        return await self._get_model(
            key=self.point_cache_key(
                latitude=latitude,
                longitude=longitude,
            ),
            model_type=NWSPointResponse,
        )

    async def set_point(
        self,
        *,
        latitude: float,
        longitude: float,
        point: NWSPointResponse,
    ) -> bool:
        """Cache NWS point metadata."""

        return await self._set_model(
            key=self.point_cache_key(
                latitude=latitude,
                longitude=longitude,
            ),
            value=point,
            ttl_seconds=(
                self.settings
                .nws_point_cache_ttl_seconds
            ),
        )

    async def get_hourly_forecast(
        self,
        *,
        forecast_url: str,
    ) -> NWSHourlyForecastResponse | None:
        """Return a cached hourly forecast."""

        return await self._get_model(
            key=self.hourly_forecast_cache_key(
                forecast_url
            ),
            model_type=NWSHourlyForecastResponse,
        )

    async def set_hourly_forecast(
        self,
        *,
        forecast_url: str,
        forecast: NWSHourlyForecastResponse,
    ) -> bool:
        """Cache an hourly forecast."""

        return await self._set_model(
            key=self.hourly_forecast_cache_key(
                forecast_url
            ),
            value=forecast,
            ttl_seconds=(
                self.settings
                .nws_hourly_forecast_cache_ttl_seconds
            ),
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "NWSCache":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()