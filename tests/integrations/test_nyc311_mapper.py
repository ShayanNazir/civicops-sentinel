from app.integrations.nyc311.mapper import map_nyc311_record
from app.integrations.nyc311.schemas import NYC311Record


def test_mapper_builds_incident_values() -> None:
    record = NYC311Record(
        unique_key="12345678",
        created_date="2026-07-24T13:00:00.000",
        agency="DOT",
        agency_name="Department of Transportation",
        complaint_type="Street Condition",
        descriptor="Pothole",
        borough="BROOKLYN",
        status="Open",
        latitude="40.712800",
        longitude="-74.006000",
    )

    mapped = map_nyc311_record(record)

    assert mapped is not None
    assert mapped["source"] == "nyc311"
    assert mapped["external_id"] == "12345678"
    assert mapped["description"] == "Street Condition: Pothole"
    assert mapped["context_data"]["agency"] == "DOT"
    assert mapped["context_data"]["borough"] == "BROOKLYN"


def test_mapper_skips_record_without_coordinates() -> None:
    record = NYC311Record(
        unique_key="87654321",
        created_date="2026-07-24T13:00:00.000",
        agency="DEP",
        complaint_type="Water System",
    )

    mapped = map_nyc311_record(record)

    assert mapped is None