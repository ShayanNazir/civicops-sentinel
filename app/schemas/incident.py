from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    source: str = Field(default="manual", min_length=2, max_length=50)
    external_id: str | None = Field(default=None, max_length=255)
    description: str = Field(min_length=5, max_length=5_000)
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(ge=-180, le=180)
    media_urls: list[str] = Field(default_factory=list, max_length=10)
    context_data: dict = Field(default_factory=dict)


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime
