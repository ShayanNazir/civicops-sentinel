from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NWSSchema(BaseModel):
    """Base configuration for NWS response schemas."""

    model_config = ConfigDict(
        populate_by_name=True,
        extra="ignore",
    )


class NWSPointProperties(NWSSchema):
    """Forecast metadata associated with one coordinate."""

    cwa: str
    grid_id: str = Field(alias="gridId")
    grid_x: int = Field(alias="gridX")
    grid_y: int = Field(alias="gridY")

    forecast_url: str = Field(alias="forecast")
    forecast_hourly_url: str = Field(alias="forecastHourly")
    forecast_grid_data_url: str = Field(alias="forecastGridData")
    observation_stations_url: str = Field(alias="observationStations")

    time_zone: str = Field(alias="timeZone")
    radar_station: str | None = Field(
        default=None,
        alias="radarStation",
    )


class NWSPointResponse(NWSSchema):
    """Validated response from the NWS points endpoint."""

    properties: NWSPointProperties


class NWSQuantitativeValue(NWSSchema):
    """A measurement represented by a unit and value."""

    unit_code: str = Field(alias="unitCode")
    value: float | None = None


class NWSForecastPeriod(NWSSchema):
    """One period from an NWS forecast response."""

    number: int
    name: str

    start_time: datetime = Field(alias="startTime")
    end_time: datetime = Field(alias="endTime")
    is_daytime: bool = Field(alias="isDaytime")

    temperature: float
    temperature_unit: str = Field(alias="temperatureUnit")
    temperature_trend: str | None = Field(
        default=None,
        alias="temperatureTrend",
    )

    probability_of_precipitation: NWSQuantitativeValue | None = Field(
        default=None,
        alias="probabilityOfPrecipitation",
    )
    dewpoint: NWSQuantitativeValue | None = None
    relative_humidity: NWSQuantitativeValue | None = Field(
        default=None,
        alias="relativeHumidity",
    )

    wind_speed: str = Field(alias="windSpeed")
    wind_direction: str = Field(alias="windDirection")

    icon: str
    short_forecast: str = Field(alias="shortForecast")
    detailed_forecast: str = Field(alias="detailedForecast")


class NWSHourlyForecastProperties(NWSSchema):
    """Metadata and periods from an hourly forecast."""

    units: str

    forecast_generator: str | None = Field(
        default=None,
        alias="forecastGenerator",
    )
    generated_at: datetime | None = Field(
        default=None,
        alias="generatedAt",
    )
    update_time: datetime= Field(
        alias="updateTime"
    )
    valid_times: str | None = Field(
        default=None,
        alias="validTimes",
    )

    periods: list[NWSForecastPeriod]


class NWSHourlyForecastResponse(NWSSchema):
    """Validated response from an hourly forecast URL."""

    properties: NWSHourlyForecastProperties
