"""
Data Source Models

Defines models for tracking data sources and metadata about where data came from.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class DataSourceType(str, Enum):
    """Type of data source."""

    EYBL = "eybl"  # Nike EYBL
    FIBA = "fiba"  # FIBA Youth
    PSAL = "psal"  # NYC PSAL
    MN_HUB = "mn_hub"  # Minnesota Basketball Hub
    GRIND_SESSION = "grind_session"  # Grind Session
    OTE = "ote"  # Overtime Elite
    ANGT = "angt"  # NextGen EuroLeague / ANGT
    OSBA = "osba"  # OSBA Canada
    PLAYHQ = "playhq"  # PlayHQ Australia
    UNKNOWN = "unknown"  # Unknown/other source


class DataSourceRegion(str, Enum):
    """Geographic region of data source."""

    US = "us"
    CANADA = "canada"
    EUROPE = "europe"
    AUSTRALIA = "australia"
    GLOBAL = "global"


class DataQualityFlag(str, Enum):
    """Quality flags for data validation."""

    COMPLETE = "complete"  # All expected data present
    PARTIAL = "partial"  # Some data missing
    SUSPECT = "suspect"  # Data present but questionable
    UNVERIFIED = "unverified"  # Not yet validated
    VERIFIED = "verified"  # Manually verified as correct


class DataSource(BaseModel):
    """
    Metadata about where data came from.

    Tracks the source, retrieval time, and quality flags for all data.
    """

    source_type: DataSourceType = Field(description="Type of data source")
    source_name: str = Field(description="Human-readable source name")
    source_url: Optional[HttpUrl] = Field(default=None, description="Source URL")
    region: DataSourceRegion = Field(description="Geographic region")
    retrieved_at: datetime = Field(
        default_factory=datetime.utcnow, description="When data was retrieved"
    )
    quality_flag: DataQualityFlag = Field(
        default=DataQualityFlag.UNVERIFIED, description="Data quality assessment"
    )
    raw_html_cached: bool = Field(default=False, description="Whether raw HTML is cached")
    cache_key: Optional[str] = Field(default=None, description="Cache key for raw data")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "eybl",
                "source_name": "Nike EYBL",
                "source_url": "https://nikeeyb.com/stats",
                "region": "us",
                "retrieved_at": "2025-11-11T12:00:00Z",
                "quality_flag": "complete",
                "raw_html_cached": True,
                "cache_key": "eybl_stats_20251111",
                "notes": "Full season stats retrieved successfully",
            }
        }


class RateLimitStatus(BaseModel):
    """Current rate limit status for a data source."""

    source_type: DataSourceType = Field(description="Data source type")
    requests_made: int = Field(ge=0, description="Requests made in current window")
    requests_allowed: int = Field(ge=1, description="Requests allowed per window")
    window_reset_at: datetime = Field(description="When rate limit window resets")
    is_limited: bool = Field(description="Whether currently rate limited")

    @property
    def requests_remaining(self) -> int:
        """Calculate remaining requests in current window."""
        return max(0, self.requests_allowed - self.requests_made)

    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage of rate limit."""
        return (self.requests_made / self.requests_allowed) * 100

    class Config:
        json_schema_extra = {
            "example": {
                "source_type": "eybl",
                "requests_made": 15,
                "requests_allowed": 30,
                "window_reset_at": "2025-11-11T12:01:00Z",
                "is_limited": False,
            }
        }
