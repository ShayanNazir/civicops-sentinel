import asyncio
from dataclasses import dataclass
from typing import Literal

from app.integrations.nws.cache import NWSCache
from app.integrations.nws.client import NWSClient
from app.integrations.nws.schemas import (
    NWSHourlyForecastResponse,
    NWSPointResponse,
)

NWSDataSource = Literal[
    "redis",
    "network",
]


@dataclass(frozen=True, slots=True)
class NWSPointLoadResult:
    """Point metadata and its source."""

    response: NWSPointResponse
    source: NWSDataSource


@dataclass(frozen=True, slots=True)
class NWSHourlyForecastLoadResult:
    """Hourly forecast and its source."""

    response: NWSHourlyForecastResponse
    source: NWSDataSource


class NWSProvider:
    """Load NWS responses through Redis and the network."""

    def __init__(
        self,
        client: NWSClient,
        cache: NWSCache,
    ) -> None:
        self.client = client
        self.cache = cache

        self._point_lock = asyncio.Lock()
        self._forecast_lock = asyncio.Lock()

    async def get_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> NWSPointLoadResult:
        cached_point = await self.cache.get_point(
            latitude=latitude,
            longitude=longitude,
        )

        if cached_point is not None:
            return NWSPointLoadResult(
                response=cached_point,
                source="redis",
            )

        async with self._point_lock:
            cached_point = await self.cache.get_point(
                latitude=latitude,
                longitude=longitude,
            )

            if cached_point is not None:
                return NWSPointLoadResult(
                    response=cached_point,
                    source="redis",
                )

            point = await self.client.fetch_point(
                latitude=latitude,
                longitude=longitude,
            )

            await self.cache.set_point(
                latitude=latitude,
                longitude=longitude,
                point=point,
            )

            return NWSPointLoadResult(
                response=point,
                source="network",
            )

    async def get_hourly_forecast(
        self,
        *,
        forecast_url: str,
    ) -> NWSHourlyForecastLoadResult:
        cached_forecast = (
            await self.cache.get_hourly_forecast(
                forecast_url=forecast_url,
            )
        )

        if cached_forecast is not None:
            return NWSHourlyForecastLoadResult(
                response=cached_forecast,
                source="redis",
            )

        async with self._forecast_lock:
            cached_forecast = (
                await self.cache.get_hourly_forecast(
                    forecast_url=forecast_url,
                )
            )

            if cached_forecast is not None:
                return NWSHourlyForecastLoadResult(
                    response=cached_forecast,
                    source="redis",
                )

            forecast = (
                await self.client.fetch_hourly_forecast(
                    forecast_url=forecast_url,
                )
            )

            await self.cache.set_hourly_forecast(
                forecast_url=forecast_url,
                forecast=forecast,
            )

            return NWSHourlyForecastLoadResult(
                response=forecast,
                source="network",
            )