from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.integrations.nws.schemas import (
    NWSHourlyForecastResponse,
    NWSPointResponse,
)

RETRYABLE_STATUS_CODES = {
    429,
    500,
    502,
    503,
    504,
}

ModelT = TypeVar(
    "ModelT",
    bound=BaseModel,
)


class NWSClientError(RuntimeError):
    """Raised when NWS data cannot be retrieved or validated."""


class NWSClient:
    """Asynchronous client for the NWS weather API."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        *,
        max_retries: int | None = None,
        retry_base_delay: float | None = None,
        sleep: Callable[
            [float],
            Awaitable[None],
        ] = asyncio.sleep,
    ) -> None:
        self.settings = settings or get_settings()

        self.max_retries = max_retries if max_retries is not None else self.settings.nws_max_retries
        self.retry_base_delay = (
            retry_base_delay
            if retry_base_delay is not None
            else (self.settings.nws_retry_base_delay_seconds)
        )
        self.sleep = sleep

        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")

        if self.retry_base_delay < 0:
            raise ValueError("retry_base_delay cannot be negative")

        self._owns_client = client is None

        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=(self.settings.nws_request_timeout_seconds),
                connect=5.0,
            )
        )

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/geo+json",
            "User-Agent": self.settings.nws_user_agent,
        }

    @staticmethod
    def _validate_coordinates(
        *,
        latitude: float,
        longitude: float,
    ) -> None:
        if not -90 <= latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")

        if not -180 <= longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")

    @property
    def base_url(self) -> str:
        return self.settings.nws_api_base_url.rstrip("/")

    def point_endpoint(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> str:
        """Build the NWS metadata endpoint for a coordinate."""

        self._validate_coordinates(
            latitude=latitude,
            longitude=longitude,
        )

        point = f"{latitude:.4f},{longitude:.4f}"

        return f"{self.base_url}/points/{point}"

    def _validate_nws_url(
        self,
        url: str,
    ) -> None:
        """
        Prevent requests to hosts other than the configured NWS API.

        Forecast URLs originate in NWS point responses, but this
        validation prevents accidental arbitrary external requests.
        """

        expected = urlparse(self.base_url)
        actual = urlparse(url)

        if actual.scheme != expected.scheme or actual.netloc != expected.netloc:
            raise ValueError("forecast URL must use the configured NWS API host")

    async def fetch_point(
        self,
        *,
        latitude: float,
        longitude: float,
    ) -> NWSPointResponse:
        """Fetch forecast metadata for one coordinate."""

        endpoint = self.point_endpoint(
            latitude=latitude,
            longitude=longitude,
        )

        return await self._get_model(
            endpoint,
            NWSPointResponse,
            response_name="NWS point response",
        )

    async def fetch_hourly_forecast(
        self,
        *,
        forecast_url: str,
    ) -> NWSHourlyForecastResponse:
        """Fetch a validated hourly forecast."""

        self._validate_nws_url(forecast_url)

        return await self._get_model(
            forecast_url,
            NWSHourlyForecastResponse,
            response_name="NWS hourly forecast",
        )

    async def _get_model(
        self,
        url: str,
        model_type: type[ModelT],
        *,
        response_name: str,
    ) -> ModelT:
        response = await self._get_with_retries(url)

        try:
            data = response.json()
        except ValueError as exc:
            raise NWSClientError(f"{response_name} returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise NWSClientError(f"{response_name} returned an unexpected response structure.")

        try:
            return model_type.model_validate(data)
        except ValidationError as exc:
            raise NWSClientError(f"{response_name} failed schema validation.") from exc

    async def _get_with_retries(
        self,
        url: str,
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(
                    url,
                    headers=self._headers(),
                )
            except httpx.RequestError as exc:
                last_error = exc

            else:
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        raise NWSClientError(
                            f"NWS request failed with HTTP {response.status_code}."
                        ) from exc

                    return response

                last_error = NWSClientError(
                    f"NWS temporarily returned HTTP {response.status_code}."
                )

            if attempt < self.max_retries:
                delay = self.retry_base_delay * (2**attempt)
                await self.sleep(delay)

        raise NWSClientError(
            f"NWS request failed after {self.max_retries + 1} attempts."
        ) from last_error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> NWSClient:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()
