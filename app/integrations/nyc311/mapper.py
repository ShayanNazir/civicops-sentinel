from typing import Any

from app.integrations.nyc311.schemas import NYC311Record


def build_description(record: NYC311Record) -> str:
    """Build a readable incident description from an NYC 311 record."""

    description = record.complaint_type

    if record.descriptor:
        description += f": {record.descriptor}"

    return description


def map_nyc311_record(
    record: NYC311Record,
) -> dict[str, Any] | None:
    """
    Convert an NYC 311 record into values accepted by the Incident model.

    Records without coordinates are skipped temporarily because the current
    Incident database model requires latitude and longitude.
    """

    if record.latitude is None or record.longitude is None:
        return None

    return {
        "source": "nyc311",
        "external_id": record.unique_key,
        "description": build_description(record),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "media_urls": [],
        "status": "received",
        "priority": "untriaged",
        "context_data": {
            "agency": record.agency,
            "agency_name": record.agency_name,
            "complaint_type": record.complaint_type,
            "descriptor": record.descriptor,
            "location_type": record.location_type,
            "incident_zip": record.incident_zip,
            "city": record.city,
            "borough": record.borough,
            "upstream_status": record.status,
            "source_created_at": record.created_date.isoformat(),
            "source_closed_at": (
                record.closed_date.isoformat() if record.closed_date is not None else None
            ),
        },
    }
