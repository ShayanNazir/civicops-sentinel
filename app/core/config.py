from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CivicOps Sentinel"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://civicops:civicops@localhost:5432/civicops"
    redis_url: str = "redis://localhost:6379/0"

    nyc_open_data_base_url: str = "https://data.cityofnewyork.us"
    nyc_311_dataset_id: str = "erm2-nwe9"
    nyc_open_data_app_token: str | None = None
    nyc_311_page_size: int = 100

    nyc_311_initial_lookback_hours: int = 72
    nyc_311_cursor_overlap_minutes: int = 5
    nyc_311_max_pages_per_run: int = 20

    nyc_2020_census_tracts_dataset_id: str = "63ge-mke6"
    nyc_boundary_cache_ttl_seconds: int = 86_400

    nws_api_base_url: str = "https://api.weather.gov"
    nws_user_agent: str = "civicops-sentinel/0.1.0 (github.com/ShayanNazir/civicops-sentinel)"
    nws_request_timeout_seconds: float = 20.0
    nws_max_retries: int = 3
    nws_retry_base_delay_seconds: float = 0.5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
