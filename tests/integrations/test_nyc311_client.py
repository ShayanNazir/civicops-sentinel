import json

import httpx
import pytest

from app.core.config import Settings
from app.integrations.nyc311.client import NYC311Client


@pytest.mark.asyncio
async def test_fetch_page_returns_validated_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)

        assert request.method == "POST"
        assert request.headers["X-App-Token"] == "test-token"
        assert payload["page"] == {
            "pageNumber": 1,
            "pageSize": 2,
        }
        assert "ORDER BY created_date DESC" in payload["query"]

        return httpx.Response(
            status_code=200,
            json=[
                {
                    "unique_key": "12345678",
                    "created_date": "2026-07-24T12:30:00.000",
                    "agency": "DOT",
                    "agency_name": "Department of Transportation",
                    "complaint_type": "Street Condition",
                    "descriptor": "Pothole",
                    "status": "Open",
                    "latitude": "40.712800",
                    "longitude": "-74.006000",
                }
            ],
        )

    transport = httpx.MockTransport(handler)

    settings = Settings(
        nyc_open_data_app_token="test-token",
    )

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NYC311Client(
            settings=settings,
            client=http_client,
        )

        records = await client.fetch_page(page_size=2)

    assert len(records) == 1
    assert records[0].unique_key == "12345678"
    assert records[0].complaint_type == "Street Condition"
    assert records[0].agency == "DOT"


@pytest.mark.asyncio
async def test_fetch_page_retries_temporary_failures() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1

        if attempts == 1:
            return httpx.Response(
                status_code=503,
                json={"message": "Temporarily unavailable"},
            )

        return httpx.Response(
            status_code=200,
            json=[
                {
                    "unique_key": "87654321",
                    "created_date": "2026-07-24T13:00:00.000",
                    "agency": "DEP",
                    "complaint_type": "Water System",
                }
            ],
        )

    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = NYC311Client(
            settings=Settings(),
            client=http_client,
            max_retries=1,
            retry_base_delay=0,
        )

        records = await client.fetch_page(page_size=1)

    assert attempts == 2
    assert records[0].unique_key == "87654321"
