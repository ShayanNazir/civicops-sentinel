import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.integrations.nyc311.schemas import NYC311Record

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

SELECT_COLUMNS = (
    "unique_key,"
    "created_date,"
    "closed_date,"
    "agency,"
    "agency_name,"
    "complaint_type,"
    "descriptor,"
    "location_type,"
    "incident_zip,"
    "city,"
    "borough,"
    "status,"
    "latitude,"
    "longitude"
)


class NYC311ClientError(RuntimeError):
    """Raised when NYC 311 data cannot be retrieved or validated."""


class NYC311Client:
    """Asynchronous client for the NYC 311 Socrata dataset."""

    def __init__(
        self,
        settings: Settings | None = None,
        client: httpx.AsyncClient | None = None,
        *,
        max_retries: int = 3,
        retry_base_delay: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self.sleep = sleep

        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(
                timeout=20.0,
                connect=5.0,
            )
        )

    @property
    def endpoint(self) -> str:
        base_url = self.settings.nyc_open_data_base_url.rstrip("/")
        dataset_id = self.settings.nyc_311_dataset_id

        return f"{base_url}/api/v3/views/{dataset_id}/query.json"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "civicops-sentinel/0.2.0",
        }

        token = self.settings.nyc_open_data_app_token

        if token:
            headers["X-App-Token"] = token

        return headers

    @staticmethod
    def _format_timestamp(value: datetime) -> str:
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)

        return value.isoformat(timespec="milliseconds")

    def _build_query(
        self,
        *,
        created_after: datetime | None,
        created_before: datetime | None,
    ) -> str:
        filters: list[str] = []

        if created_after is not None:
            timestamp = self._format_timestamp(created_after)
            filters.append(f"created_date >= '{timestamp}'")

        if created_before is not None:
            timestamp = self._format_timestamp(created_before)
            filters.append(f"created_date < '{timestamp}'")

        query = f"SELECT {SELECT_COLUMNS}"

        if filters:
            query += " WHERE " + " AND ".join(filters)

        # Stable ordering is essential when retrieving multiple pages.
        query += " ORDER BY created_date DESC, unique_key DESC"

        return query

    async def fetch_page(
        self,
        *,
        page_number: int = 1,
        page_size: int | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
    ) -> list[NYC311Record]:
        if page_number < 1:
            raise ValueError("page_number must be at least 1")

        resolved_page_size = page_size or self.settings.nyc_311_page_size

        if not 1 <= resolved_page_size <= 5_000:
            raise ValueError("page_size must be between 1 and 5000")

        payload: dict[str, Any] = {
            "query": self._build_query(
                created_after=created_after,
                created_before=created_before,
            ),
            "page": {
                "pageNumber": page_number,
                "pageSize": resolved_page_size,
            },
            "includeSystem": False,
            "includeSynthetic": False,
        }

        response = await self._post_with_retries(payload)

        try:
            data = response.json()
        except ValueError as exc:
            raise NYC311ClientError("NYC 311 returned invalid JSON.") from exc

        if not isinstance(data, list):
            raise NYC311ClientError("NYC 311 returned an unexpected response structure.")

        try:
            return [NYC311Record.model_validate(record) for record in data]
        except ValidationError as exc:
            raise NYC311ClientError("An NYC 311 record failed schema validation.") from exc

    async def _post_with_retries(
        self,
        payload: dict[str, Any],
    ) -> httpx.Response:
        last_error: Exception | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.post(
                    self.endpoint,
                    headers=self._headers(),
                    json=payload,
                )
            except httpx.RequestError as exc:
                last_error = exc
            else:
                if response.status_code not in RETRYABLE_STATUS_CODES:
                    try:
                        response.raise_for_status()
                    except httpx.HTTPStatusError as exc:
                        message = f"NYC 311 request failed with HTTP {response.status_code}."
                        raise NYC311ClientError(message) from exc

                    return response

                last_error = NYC311ClientError(
                    f"NYC 311 temporarily returned HTTP {response.status_code}."
                )

            if attempt < self.max_retries:
                delay = self.retry_base_delay * (2**attempt)
                await self.sleep(delay)

        raise NYC311ClientError(
            f"NYC 311 request failed after {self.max_retries + 1} attempts."
        ) from last_error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> "NYC311Client":
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc: object,
        traceback: object,
    ) -> None:
        await self.aclose()
