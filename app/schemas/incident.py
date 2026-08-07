from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class IncidentCreate(BaseModel):
    source: str = Field(
        default="manual",
        min_length=2,
        max_length=50,
    )
    external_id: str | None = Field(
        default=None,
        max_length=255,
    )
    description: str = Field(
        min_length=5,
        max_length=5_000,
    )
    latitude: Decimal = Field(ge=-90, le=90)
    longitude: Decimal = Field(
        ge=-180,
        le=180,
    )
    media_urls: list[str] = Field(
        default_factory=list,
        max_length=10,
    )
    context_data: dict = Field(default_factory=dict)


class IncidentRead(IncidentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    priority: str

    geospatial_status: str
    geospatial_enriched_at: datetime | None

    census_tract_geoid: str | None
    census_tract_code: str | None
    census_tract_label: str | None
    borough_tract_code: str | None
    borough_code: str | None
    borough_name: str | None
    nta_code: str | None
    nta_name: str | None
    cdta_code: str | None
    cdta_name: str | None

    weather_status: str = "pending"
    weather_enriched_at: datetime | None = None
    weather_requested_at: datetime | None = None

    weather_point_source: str | None = None
    weather_forecast_source: str | None = None

    nws_office: str | None = None
    nws_grid_id: str | None = None
    nws_grid_x: int | None = None
    nws_grid_y: int | None = None
    weather_time_zone: str | None = None
    weather_radar_station: str | None = None

    weather_forecast_url: str | None = None
    weather_forecast_updated_at: datetime | None = None
    weather_forecast_generated_at: datetime | None = None

    weather_period_start: datetime | None = None
    weather_period_end: datetime | None = None
    weather_is_daytime: bool | None = None

    weather_temperature: Decimal | None = None
    weather_temperature_unit: str | None = None
    weather_precipitation_probability_percent: Decimal | None = None
    weather_relative_humidity_percent: Decimal | None = None
    weather_dewpoint_value: Decimal | None = None
    weather_dewpoint_unit_code: str | None = None

    weather_wind_speed: str | None = None
    weather_wind_direction: str | None = None
    weather_short_forecast: str | None = None
    weather_detailed_forecast: str | None = None
    weather_icon_url: str | None = None

    created_at: datetime
    updated_at: datetime
