"""
Configuration Management System

Loads and validates all application settings from environment variables.
Uses Pydantic Settings for type-safe configuration with validation.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Settings
    app_name: str = Field(default="HS Basketball Players API", description="Application name")
    app_version: str = Field(default="0.1.0", description="Application version")
    environment: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    debug: bool = Field(default=True, description="Debug mode")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Logging level"
    )

    # API Settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    api_workers: int = Field(default=4, ge=1, le=16, description="Number of workers")

    # Rate Limiting (requests per minute per source)
    rate_limit_eybl: int = Field(default=30, ge=1, description="EYBL rate limit")
    rate_limit_fiba: int = Field(default=20, ge=1, description="FIBA rate limit")
    rate_limit_psal: int = Field(default=15, ge=1, description="PSAL rate limit")
    rate_limit_mn_hub: int = Field(default=20, ge=1, description="MN Hub rate limit")
    rate_limit_grind_session: int = Field(default=15, ge=1, description="Grind Session rate limit")
    rate_limit_ote: int = Field(default=25, ge=1, description="OTE rate limit")
    rate_limit_angt: int = Field(default=20, ge=1, description="ANGT rate limit")
    rate_limit_osba: int = Field(default=15, ge=1, description="OSBA rate limit")
    rate_limit_playhq: int = Field(default=25, ge=1, description="PlayHQ rate limit")
    rate_limit_default: int = Field(default=10, ge=1, description="Default rate limit")

    # Global rate limiting
    global_rate_limit_per_ip: int = Field(
        default=100, ge=1, description="Global rate limit per IP"
    )

    # Caching
    cache_enabled: bool = Field(default=True, description="Enable caching")
    cache_type: Literal["file", "redis", "memory"] = Field(
        default="file", description="Cache type"
    )
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    cache_ttl_players: int = Field(default=3600, ge=0, description="Player cache TTL (seconds)")
    cache_ttl_games: int = Field(default=1800, ge=0, description="Game cache TTL (seconds)")
    cache_ttl_stats: int = Field(default=900, ge=0, description="Stats cache TTL (seconds)")
    cache_ttl_schedules: int = Field(
        default=7200, ge=0, description="Schedule cache TTL (seconds)"
    )

    # HTTP Client Settings
    http_timeout: int = Field(default=30, ge=1, le=300, description="HTTP timeout (seconds)")
    http_max_retries: int = Field(default=3, ge=0, le=10, description="Max HTTP retries")
    http_retry_backoff: float = Field(
        default=2.0, ge=1.0, le=10.0, description="Retry backoff multiplier"
    )
    http_user_agent: str = Field(
        default="Mozilla/5.0 (compatible; HSBasketballStatsBot/0.1; "
        "+https://github.com/ghadfield32/hs_bball_players_mcp)",
        description="HTTP User-Agent header",
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./data/basketball_stats.db", description="Database URL"
    )

    # DuckDB Settings (Analytical Database)
    duckdb_enabled: bool = Field(default=True, description="Enable DuckDB analytics database")
    duckdb_path: str = Field(
        default="./data/basketball_analytics.duckdb", description="DuckDB database path"
    )
    duckdb_memory_limit: str = Field(default="2GB", description="DuckDB memory limit")
    duckdb_threads: int = Field(default=4, ge=1, le=32, description="DuckDB thread count")

    # Data Export Settings
    export_dir: str = Field(default="./data/exports", description="Export directory path")
    parquet_compression: str = Field(
        default="snappy", description="Parquet compression (snappy, gzip, zstd, lz4)"
    )
    enable_auto_export: bool = Field(
        default=False, description="Enable automatic data export to Parquet"
    )
    auto_export_interval: int = Field(
        default=3600, ge=60, description="Auto-export interval in seconds"
    )

    # Data Source Settings - EYBL
    eybl_base_url: str = Field(default="https://nikeeyb.com", description="EYBL base URL")
    eybl_enabled: bool = Field(default=True, description="Enable EYBL datasource")

    # Data Source Settings - FIBA Youth
    fiba_base_url: str = Field(
        default="https://about.fiba.basketball", description="FIBA base URL"
    )
    fiba_enabled: bool = Field(default=True, description="Enable FIBA datasource")

    # Data Source Settings - PSAL (NYC)
    psal_base_url: str = Field(default="https://www.psal.org", description="PSAL base URL")
    psal_enabled: bool = Field(default=True, description="Enable PSAL datasource")

    # Data Source Settings - Minnesota Basketball Hub
    mn_hub_base_url: str = Field(
        default="https://stats.mnbasketballhub.com", description="MN Hub base URL"
    )
    mn_hub_enabled: bool = Field(default=True, description="Enable MN Hub datasource")

    # Data Source Settings - Grind Session
    grind_session_base_url: str = Field(
        default="https://grindsession.com", description="Grind Session base URL"
    )
    grind_session_enabled: bool = Field(default=True, description="Enable Grind Session datasource")

    # Data Source Settings - Overtime Elite
    ote_base_url: str = Field(
        default="https://overtimeelite.com", description="OTE base URL"
    )
    ote_enabled: bool = Field(default=True, description="Enable OTE datasource")

    # Data Source Settings - NextGen EuroLeague / ANGT
    angt_base_url: str = Field(
        default="https://www.adidasngt.com", description="ANGT base URL"
    )
    angt_enabled: bool = Field(default=True, description="Enable ANGT datasource")

    # Data Source Settings - OSBA (Canada)
    osba_base_url: str = Field(default="https://www.osba.ca", description="OSBA base URL")
    osba_enabled: bool = Field(default=False, description="Enable OSBA datasource")

    # Data Source Settings - PlayHQ (Australia)
    playhq_base_url: str = Field(
        default="https://www.playhq.com", description="PlayHQ base URL"
    )
    playhq_enabled: bool = Field(default=False, description="Enable PlayHQ datasource")

    # Monitoring & Observability
    enable_request_logging: bool = Field(default=True, description="Enable request logging")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking")

    # Security
    api_key_enabled: bool = Field(default=False, description="Require API key")
    api_key: str = Field(default="", description="API key for authentication")
    cors_origins: str = Field(default="*", description="CORS origins (comma-separated or *)")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        """Validate CORS origins configuration."""
        if v == "*":
            return v
        # Validate it's a comma-separated list
        origins = [origin.strip() for origin in v.split(",")]
        if not all(origins):
            raise ValueError("CORS origins must be '*' or comma-separated list of URLs")
        return v

    def get_datasource_rate_limit(self, source: str) -> int:
        """Get rate limit for a specific datasource."""
        source_key = f"rate_limit_{source.lower().replace(' ', '_')}"
        return getattr(self, source_key, self.rate_limit_default)

    def get_datasource_base_url(self, source: str) -> str:
        """Get base URL for a specific datasource."""
        source_key = f"{source.lower().replace(' ', '_')}_base_url"
        return getattr(self, source_key, "")

    def is_datasource_enabled(self, source: str) -> bool:
        """Check if a specific datasource is enabled."""
        source_key = f"{source.lower().replace(' ', '_')}_enabled"
        return getattr(self, source_key, False)

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as a list."""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Using lru_cache ensures we only load settings once and reuse the same instance.
    This is important for performance and consistency across the application.

    Returns:
        Settings: Application settings instance
    """
    return Settings()


# Convenience function to get specific setting
def get_setting(key: str, default: any = None) -> any:
    """
    Get a specific setting value by key.

    Args:
        key: Setting key name
        default: Default value if key not found

    Returns:
        Setting value or default
    """
    settings = get_settings()
    return getattr(settings, key, default)
