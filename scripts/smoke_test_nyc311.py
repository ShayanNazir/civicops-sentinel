import asyncio

from app.integrations.nyc311.client import NYC311Client, NYC311ClientError


async def main() -> None:
    print("Connecting to the live NYC 311 API...")

    try:
        async with NYC311Client() as client:
            records = await client.fetch_page(page_size=5)
    except NYC311ClientError as exc:
        print(f"NYC 311 smoke test failed: {exc}")
        raise SystemExit(1) from exc

    print(f"Successfully retrieved {len(records)} records.")

    if not records:
        print("The request succeeded, but no records were returned.")
        return

    print("\nLatest retrieved incidents:\n")

    for index, record in enumerate(records, start=1):
        print(f"Record {index}")
        print(f"  Unique key: {record.unique_key}")
        print(f"  Created: {record.created_date}")
        print(f"  Agency: {record.agency}")
        print(f"  Complaint: {record.complaint_type}")
        print(f"  Descriptor: {record.descriptor or 'Not provided'}")
        print(f"  Borough: {record.borough or 'Not provided'}")
        print(f"  Status: {record.status or 'Not provided'}")
        print(f"  Coordinates: {record.latitude}, {record.longitude}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
