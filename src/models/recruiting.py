"""
Recruiting Data Models

Defines models for basketball player recruiting rankings, offers, and predictions.
Used for tracking college recruitment process and forecasting college destinations.

Author: Claude Code
Date: 2025-11-14
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .player import Position
from .source import DataSource


class RecruitingService(str, Enum):
    """Recruiting ranking service."""

    COMPOSITE = "composite"  # 247Sports Composite (aggregates all services)
    SPORTS_247 = "247sports"  # 247Sports rankings
    ESPN = "espn"  # ESPN recruiting
    RIVALS = "rivals"  # Rivals (now part of On3)
    ON3 = "on3"  # On3 rankings
    PREP_HOOPS = "prephoops"  # PrepHoops
    UNKNOWN = "unknown"


class OfferStatus(str, Enum):
    """Status of a college offer."""

    OFFERED = "offered"  # School has offered
    COMMITTED = "committed"  # Player has committed
    DECOMMITTED = "decommitted"  # Player decommitted
    SIGNED = "signed"  # Player signed LOI
    WITHDRAWN = "withdrawn"  # School withdrew offer
    DECLINED = "declined"  # Player declined offer
    UNKNOWN = "unknown"


class ConferenceLevel(str, Enum):
    """College conference level classification."""

    POWER_6 = "power_6"  # ACC, Big Ten, Big 12, Big East, Pac-12, SEC
    HIGH_MAJOR = "high_major"  # Other strong D1 conferences
    MID_MAJOR = "mid_major"  # Mid-tier D1 conferences
    LOW_MAJOR = "low_major"  # Lower D1 conferences
    D2 = "d2"  # Division 2
    D3 = "d3"  # Division 3
    NAIA = "naia"  # NAIA
    JUCO = "juco"  # Junior College
    INTERNATIONAL = "international"  # International leagues
    UNKNOWN = "unknown"


class RecruitingRank(BaseModel):
    """
    Player recruiting ranking from a service.

    Tracks national, position, and state rankings along with star ratings.
    """

    # Identity
    player_id: str = Field(description="Player ID from recruiting service")
    player_name: str = Field(min_length=1, description="Player name")
    player_uid: Optional[str] = Field(
        default=None,
        description="Universal player ID (from identity service)"
    )

    # Rankings
    rank_national: Optional[int] = Field(
        default=None,
        ge=1,
        description="National ranking (overall)"
    )
    rank_position: Optional[int] = Field(
        default=None,
        ge=1,
        description="Position ranking"
    )
    rank_state: Optional[int] = Field(
        default=None,
        ge=1,
        description="State ranking"
    )

    # Rating
    stars: Optional[int] = Field(
        default=None,
        ge=3,
        le=5,
        description="Star rating (3-5 stars)"
    )
    rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Numerical rating (normalized 0-1)"
    )

    # Recruiting Service
    service: RecruitingService = Field(description="Recruiting service source")

    # Player Info
    class_year: int = Field(
        ge=2020,
        le=2035,
        description="High school graduation year"
    )
    position: Optional[Position] = Field(default=None, description="Primary position")
    height: Optional[str] = Field(default=None, description="Height (e.g., '6-5')")
    weight: Optional[int] = Field(
        default=None,
        ge=100,
        le=400,
        description="Weight in pounds"
    )

    # Location
    school: Optional[str] = Field(default=None, description="High school name")
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State")
    country: Optional[str] = Field(default="USA", description="Country")

    # Commitment Status
    committed_to: Optional[str] = Field(
        default=None,
        description="College player is committed to"
    )
    commitment_date: Optional[datetime] = Field(
        default=None,
        description="Date of commitment"
    )

    # Profile URLs
    profile_url: Optional[str] = Field(
        default=None,
        description="Player profile URL on recruiting site"
    )

    # Metadata
    data_source: DataSource = Field(description="Where this data came from")

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "247_12345",
                "player_name": "John Smith",
                "player_uid": "john_smith_2026_lincoln_hs",
                "rank_national": 15,
                "rank_position": 3,
                "rank_state": 1,
                "stars": 5,
                "rating": 0.9850,
                "service": "247sports",
                "class_year": 2026,
                "position": "SG",
                "height": "6-5",
                "weight": 185,
                "school": "Lincoln High School",
                "city": "Portland",
                "state": "OR",
                "committed_to": "Duke University",
                "commitment_date": "2025-09-15T12:00:00Z",
                "profile_url": "https://247sports.com/player/john-smith-12345",
                "data_source": {
                    "source_type": "247sports",
                    "source_name": "247Sports",
                    "region": "us",
                    "quality_flag": "verified",
                },
            }
        }


class CollegeOffer(BaseModel):
    """
    College offer for a player.

    Tracks recruiting offers from college programs.
    """

    # Identity
    player_id: str = Field(description="Player ID")
    player_name: str = Field(min_length=1, description="Player name")
    player_uid: Optional[str] = Field(
        default=None,
        description="Universal player ID"
    )

    # College Info
    college_name: str = Field(min_length=1, description="College/university name")
    college_conference: Optional[str] = Field(
        default=None,
        description="Conference (e.g., 'ACC', 'Big Ten')"
    )
    conference_level: Optional[ConferenceLevel] = Field(
        default=None,
        description="Conference level classification"
    )

    # Offer Details
    offer_date: Optional[datetime] = Field(
        default=None,
        description="Date offer was extended"
    )
    offer_status: OfferStatus = Field(
        default=OfferStatus.OFFERED,
        description="Status of the offer"
    )
    status_date: Optional[datetime] = Field(
        default=None,
        description="Date of last status change"
    )

    # Additional Context
    scholarship_type: Optional[str] = Field(
        default=None,
        description="Type of scholarship (full, partial, etc.)"
    )
    notes: Optional[str] = Field(default=None, description="Additional notes")

    # Metadata
    data_source: DataSource = Field(description="Where this data came from")

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "247_12345",
                "player_name": "John Smith",
                "player_uid": "john_smith_2026_lincoln_hs",
                "college_name": "Duke University",
                "college_conference": "ACC",
                "conference_level": "power_6",
                "offer_date": "2025-06-15T10:00:00Z",
                "offer_status": "committed",
                "status_date": "2025-09-15T12:00:00Z",
                "scholarship_type": "full",
                "data_source": {
                    "source_type": "247sports",
                    "source_name": "247Sports",
                    "region": "us",
                },
            }
        }


class RecruitingPrediction(BaseModel):
    """
    Crystal Ball or similar recruiting prediction.

    Expert predictions for where a player will commit.
    """

    # Identity
    player_id: str = Field(description="Player ID")
    player_name: str = Field(min_length=1, description="Player name")
    player_uid: Optional[str] = Field(
        default=None,
        description="Universal player ID"
    )

    # Prediction
    college_predicted: str = Field(
        min_length=1,
        description="Predicted college destination"
    )
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Confidence level (0.0 to 1.0)"
    )
    confidence_level: Optional[str] = Field(
        default=None,
        description="Confidence description (e.g., 'High', 'Medium', 'Low')"
    )

    # Predictor Info
    predictor: str = Field(description="Expert name or service making prediction")
    predictor_organization: Optional[str] = Field(
        default=None,
        description="Organization (e.g., '247Sports', 'ESPN')"
    )

    # Timing
    prediction_date: datetime = Field(description="Date prediction was made")
    last_updated: Optional[datetime] = Field(
        default=None,
        description="Last time prediction was updated"
    )

    # Additional Context
    reasoning: Optional[str] = Field(
        default=None,
        description="Reasoning for the prediction"
    )
    other_contenders: Optional[List[str]] = Field(
        default=None,
        description="Other schools in consideration"
    )

    # Metadata
    data_source: DataSource = Field(description="Where this data came from")

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "247_12345",
                "player_name": "John Smith",
                "player_uid": "john_smith_2026_lincoln_hs",
                "college_predicted": "Duke University",
                "confidence": 0.95,
                "confidence_level": "High",
                "predictor": "Jerry Meyer",
                "predictor_organization": "247Sports",
                "prediction_date": "2025-08-01T09:00:00Z",
                "last_updated": "2025-09-01T14:30:00Z",
                "reasoning": "Family connections, Duke leading in recruitment",
                "other_contenders": ["North Carolina", "Kentucky", "Kansas"],
                "data_source": {
                    "source_type": "247sports",
                    "source_name": "247Sports Crystal Ball",
                    "region": "us",
                },
            }
        }


class RecruitingProfile(BaseModel):
    """
    Comprehensive recruiting profile aggregating all recruiting data.

    Combines rankings, offers, and predictions for a single player.
    """

    # Identity
    player_uid: str = Field(description="Universal player ID")
    player_name: str = Field(description="Player name")

    # Rankings (from multiple services)
    rankings: List[RecruitingRank] = Field(
        default_factory=list,
        description="Rankings from all services"
    )

    # Composite/Best Ranking
    best_national_rank: Optional[int] = Field(
        default=None,
        description="Best national ranking across all services"
    )
    composite_rank: Optional[int] = Field(
        default=None,
        description="247Sports Composite ranking"
    )
    composite_rating: Optional[float] = Field(
        default=None,
        description="Composite rating"
    )
    max_stars: Optional[int] = Field(
        default=None,
        description="Highest star rating received"
    )

    # Offers
    offers: List[CollegeOffer] = Field(
        default_factory=list,
        description="All college offers"
    )
    offer_count: int = Field(default=0, description="Total number of offers")
    power_6_offers: int = Field(default=0, description="Number of Power 6 offers")

    # Commitment Status
    is_committed: bool = Field(default=False, description="Has player committed?")
    committed_to: Optional[str] = Field(default=None, description="Committed college")
    commitment_date: Optional[datetime] = Field(
        default=None,
        description="Commitment date"
    )

    # Predictions
    predictions: List[RecruitingPrediction] = Field(
        default_factory=list,
        description="Expert predictions"
    )
    prediction_consensus: Optional[str] = Field(
        default=None,
        description="Most predicted college"
    )
    prediction_confidence: Optional[float] = Field(
        default=None,
        description="Average confidence of predictions"
    )

    # Metadata
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last time profile was updated"
    )

    @field_validator("offer_count", mode="before")
    @classmethod
    def count_offers(cls, v, info):
        """Auto-calculate offer count from offers list."""
        if "offers" in info.data:
            return len(info.data["offers"])
        return v

    @field_validator("power_6_offers", mode="before")
    @classmethod
    def count_power_6_offers(cls, v, info):
        """Auto-calculate Power 6 offers."""
        if "offers" in info.data:
            return len([
                o for o in info.data["offers"]
                if o.conference_level == ConferenceLevel.POWER_6
            ])
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "player_uid": "john_smith_2026_lincoln_hs",
                "player_name": "John Smith",
                "rankings": [
                    {
                        "service": "247sports",
                        "rank_national": 15,
                        "stars": 5,
                    },
                    {
                        "service": "espn",
                        "rank_national": 18,
                        "stars": 5,
                    }
                ],
                "best_national_rank": 15,
                "composite_rank": 16,
                "max_stars": 5,
                "offers": [
                    {"college_name": "Duke", "conference_level": "power_6"},
                    {"college_name": "North Carolina", "conference_level": "power_6"},
                ],
                "offer_count": 15,
                "power_6_offers": 10,
                "is_committed": True,
                "committed_to": "Duke University",
                "commitment_date": "2025-09-15T12:00:00Z",
                "predictions": [
                    {
                        "college_predicted": "Duke",
                        "confidence": 0.95,
                        "predictor": "Jerry Meyer"
                    }
                ],
                "prediction_consensus": "Duke University",
                "prediction_confidence": 0.92,
            }
        }
