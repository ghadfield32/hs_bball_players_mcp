"""
Player Models

Defines comprehensive player data structures with full validation.
"""

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .source import DataSource


class Position(str, Enum):
    """Basketball position."""

    PG = "PG"  # Point Guard
    SG = "SG"  # Shooting Guard
    SF = "SF"  # Small Forward
    PF = "PF"  # Power Forward
    C = "C"  # Center
    G = "G"  # Guard (generic)
    F = "F"  # Forward (generic)
    GF = "GF"  # Guard-Forward
    FC = "FC"  # Forward-Center


class PlayerLevel(str, Enum):
    """Player competition level."""

    HIGH_SCHOOL = "high_school"
    PREP = "prep"  # Prep school
    GRASSROOTS = "grassroots"  # AAU/club
    JUNIOR = "junior"  # U16/U17/U18
    ACADEMY = "academy"  # European academy
    UNKNOWN = "unknown"


class Player(BaseModel):
    """
    Comprehensive player data model.

    Captures all available player information with validation.
    """

    # Identity
    player_id: str = Field(description="Unique player identifier (source-specific)")
    first_name: str = Field(min_length=1, description="Player first name")
    last_name: str = Field(min_length=1, description="Player last name")
    full_name: Optional[str] = Field(default=None, description="Full display name")

    # Physical Attributes
    height_inches: Optional[int] = Field(
        default=None, ge=48, le=96, description="Height in inches"
    )
    weight_lbs: Optional[int] = Field(default=None, ge=80, le=400, description="Weight in pounds")
    position: Optional[Position] = Field(default=None, description="Primary position")
    secondary_position: Optional[Position] = Field(default=None, description="Secondary position")

    # School & Team Information
    school_name: Optional[str] = Field(default=None, description="Current school")
    school_city: Optional[str] = Field(default=None, description="School city")
    school_state: Optional[str] = Field(default=None, description="School state/province")
    school_country: Optional[str] = Field(default=None, description="School country")
    team_name: Optional[str] = Field(default=None, description="Current team")
    jersey_number: Optional[int] = Field(
        default=None, ge=0, le=99, description="Jersey number"
    )

    # Academic Info
    grad_year: Optional[int] = Field(
        default=None, ge=2020, le=2035, description="High school graduation year"
    )
    birth_date: Optional[date] = Field(default=None, description="Date of birth")

    # Competition Level
    level: PlayerLevel = Field(default=PlayerLevel.UNKNOWN, description="Competition level")

    # Contact & Social (when available)
    email: Optional[str] = Field(default=None, description="Email address")
    phone: Optional[str] = Field(default=None, description="Phone number")
    twitter_handle: Optional[str] = Field(default=None, description="Twitter/X handle")
    instagram_handle: Optional[str] = Field(default=None, description="Instagram handle")

    # Metadata
    profile_url: Optional[str] = Field(default=None, description="Player profile URL")
    photo_url: Optional[str] = Field(default=None, description="Player photo URL")
    data_source: DataSource = Field(description="Where this data came from")

    @field_validator("full_name", mode="before")
    @classmethod
    def set_full_name(cls, v: Optional[str], info) -> str:
        """Auto-generate full_name if not provided."""
        if v:
            return v
        # Access other field values from info.data
        first = info.data.get("first_name", "")
        last = info.data.get("last_name", "")
        return f"{first} {last}".strip()

    @property
    def height_feet_inches(self) -> Optional[str]:
        """Get height in feet'inches" format."""
        if self.height_inches is None:
            return None
        feet = self.height_inches // 12
        inches = self.height_inches % 12
        return f"{feet}'{inches}\""

    @property
    def age(self) -> Optional[int]:
        """Calculate age from birth_date."""
        if self.birth_date is None:
            return None
        today = date.today()
        age = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "eybl_12345",
                "first_name": "John",
                "last_name": "Smith",
                "full_name": "John Smith",
                "height_inches": 75,
                "weight_lbs": 185,
                "position": "SG",
                "secondary_position": "SF",
                "school_name": "Lincoln High School",
                "school_city": "Portland",
                "school_state": "OR",
                "school_country": "USA",
                "team_name": "Portland Basketball Club",
                "jersey_number": 23,
                "grad_year": 2026,
                "birth_date": "2008-03-15",
                "level": "grassroots",
                "profile_url": "https://nikeeyb.com/player/12345",
                "data_source": {
                    "source_type": "eybl",
                    "source_name": "Nike EYBL",
                    "region": "us",
                    "quality_flag": "complete",
                },
            }
        }


class PlayerIdentifier(BaseModel):
    """
    Lightweight player identifier for lookups and linking.

    Used when we don't need full player data.
    """

    player_id: str = Field(description="Player ID")
    full_name: str = Field(description="Player full name")
    school_name: Optional[str] = Field(default=None, description="School name")
    grad_year: Optional[int] = Field(default=None, description="Graduation year")
    source_type: str = Field(description="Source type")

    def __str__(self) -> str:
        """String representation."""
        parts = [self.full_name]
        if self.school_name:
            parts.append(f"({self.school_name})")
        if self.grad_year:
            parts.append(f"'{self.grad_year % 100:02d}")
        return " ".join(parts)
