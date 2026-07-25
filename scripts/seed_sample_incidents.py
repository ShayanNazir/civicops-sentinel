import asyncio

import httpx

API_URL = "http://localhost:8000/api/v1/incidents"

SAMPLES = [
    {
        "source": "seed",
        "external_id": "seed-001",
        "description": "Large pothole in the right lane causing vehicles to swerve.",
        "latitude": 40.748817,
        "longitude": -73.985428,
        "media_urls": [],
        "context_data": {"borough": "Manhattan"},
    },
    {
        "source": "seed",
        "external_id": "seed-002",
        "description": "Fallen tree partially blocking the roadway after a storm.",
        "latitude": 40.678178,
        "longitude": -73.944158,
        "media_urls": [],
        "context_data": {"borough": "Brooklyn"},
    },
    {
        "source": "seed",
        "external_id": "seed-003",
        "description": "Flooded intersection with water covering the curb and crosswalk.",
        "latitude": 40.728224,
        "longitude": -73.794852,
        "media_urls": [],
        "context_data": {"borough": "Queens"},
    },
]


async def main() -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        for sample in SAMPLES:
            response = await client.post(API_URL, json=sample)
            if response.status_code == 201:
                body = response.json()
                print(f"Created {body['id']}: {body['description']}")
            elif response.status_code == 409:
                print(f"Already exists: {sample['external_id']}")
            else:
                print(f"Failed {sample['external_id']}: {response.status_code} {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
