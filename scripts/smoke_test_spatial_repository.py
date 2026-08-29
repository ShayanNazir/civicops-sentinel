import asyncio

from app.db.session import AsyncSessionLocal
from app.repositories.incidents import IncidentRepository


async def main() -> None:
    latitude = 40.7580
    longitude = -73.9855
    radius_meters = 1_000

    print("Spatial repository smoke test")
    print(f"Center: {latitude}, {longitude}")
    print(f"Radius: {radius_meters} meters")
    print()

    async with AsyncSessionLocal() as db:
        nearby = await IncidentRepository.find_within_radius(
            db,
            latitude=latitude,
            longitude=longitude,
            radius_meters=radius_meters,
            limit=10,
        )

    print(f"Found {len(nearby)} incident(s).")
    print()

    for result in nearby:
        incident = result.incident

        print(
            f"{incident.external_id} | "
            f"{incident.borough_name} | "
            f"{result.distance_meters:.1f} meters"
        )


if __name__ == "__main__":
    asyncio.run(main())
