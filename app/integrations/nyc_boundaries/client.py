import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.integrations.nyc_boundaries.index import (
    NYCBoundaryIndex,
)
from app.integrations.nyc_boundaries.schemas import (
    CensusTractFeatureCollection,
)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class NYCBoundaryClientError(RuntimeError):
    """Raised when NYC boundary data cannot be retrieved."""


class NYCBoundaryClient:
    """Asynchronous client for NYC census-tract boundaries."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        *,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
        sleep: Callable[
            [float],
            Awaitable[None],
        ] = asyncio.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.sleep = sleep

        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=60.0,
                connect=10.0,
            )
        )

    @property
    def endpoint(self) -> str:
        base_url = self.settings.nyc_open_data_base_url.rstrip("/")
        dataset_id = self.settings.nyc_2020_census_tracts_dataset_id

        return f"{base_url}/resource/{dataset_id}.geojson"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/geo+json",
            "User-Agent": "civicops-sentinel/0.3.0",
        }

        token = self.settings.nyc_open_data_app_token

        if token:
            headers["X-App-Token"] = token

        return headers

    async def fetch_feature_collection(
        self,
    ) -> CensusTractFeatureCollection:
        """Download and validate the NYC tract GeoJSON."""

        response = await self._get_with_retries(
            params={
                "$limit": "5000",
            }
        )

        try:
            payload: Any = response.json()
        except ValueError as exc:
            raise NYCBoundaryClientError("NYC boundary service returned invalid JSON") from exc

        try:
            feature_collection = CensusTractFeatureCollection.model_validate(payload)
        except ValidationError as exc:
            raise NYCBoundaryClientError("NYC boundary response failed validation") from exc

        if not feature_collection.features:
            raise NYCBoundaryClientError("NYC boundary response contained no features")

        return feature_collection

    async def fetch_index(self) -> NYCBoundaryIndex:
        """Download the boundaries and construct a spatial index."""

        feature_collection = await self.fetch_feature_collection()

        return NYCBoundaryIndex(feature_collection.features)

    async def _get_with_retries(
        self,
        *,
        params: dict[str, str],
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(
                    self.endpoint,
                    headers=self._headers(),
                    params=params,
                )
            except httpx.RequestError as exc:
                last_error = exc
            else:
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        message = f"NYC boundary request failed with HTTP {response.status_code}"
                        raise NYCBoundaryClientError(message) from exc

                    return response

                last_error = NYCBoundaryClientError(
                    f"NYC boundary service temporarily returned HTTP {response.status_code}"
                )

            if attempt < self.max_retries:
                delay = self.retry_base_delay * (2**attempt)
                await self.sleep(delay)

        raise NYCBoundaryClientError(
            f"NYC boundary request failed after {self.max_retries + 1} attempts"
        ) from last_error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(
        self,
    ) -> "NYCBoundaryClient":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()
