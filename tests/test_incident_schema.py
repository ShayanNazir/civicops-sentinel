import pytest
from pydantic import ValidationError

from app.schemas.incident import IncidentCreate


def test_incident_rejects_invalid_latitude() -> None:
    with pytest.raises(ValidationError):
        IncidentCreate(
            description="A valid incident description.",
            latitude=120,
            longitude=-74,
        )


def test_incident_defaults_are_safe() -> None:
    incident = IncidentCreate(
        description="A valid incident description.",
        latitude=40.7,
        longitude=-74.0,
    )

    assert incident.source == "manual"
    assert incident.media_urls == []
    assert incident.context_data == {}
