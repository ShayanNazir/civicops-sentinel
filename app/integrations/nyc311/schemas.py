from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class NYC311Record(BaseModel):
    """Validated subset of an NYC 311 service-request record."""

    model_config = ConfigDict(extra="ignore")

    unique_key: str
    created_date: datetime
    closed_date: datetime | None = None

    agency: str
    agency_name: str | None = None

    complaint_type: str
    descriptor: str | None = None
    location_type: str | None = None

    incident_zip: str | None = None
    city: str | None = None
    borough: str | None = None
    status: str | None = None

    latitude: Decimal | None = None
    longitude: Decimal | None = None
