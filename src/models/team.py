"""
Team Models

Defines team data structures with validation.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from .source import DataSource


class TeamLevel(str, Enum):
    """Team competition level."""

    HIGH_SCHOOL_VARSITY = "high_school_varsity"
    HIGH_SCHOOL_JV = "high_school_jv"
    PREP_SCHOOL = "prep_school"
    GRASSROOTS = "grassroots"  # AAU/club
    JUNIOR_NATIONAL = "junior_national"  # U16/U17/U18
    ACADEMY = "academy"
    UNKNOWN = "unknown"


class Team(BaseModel):
    """
    Comprehensive team data model.

    Represents a basketball team at any level.
    """

    # Identity
    team_id: str = Field(description="Unique team identifier")
    team_name: str = Field(min_length=1, description="Team name")
    short_name: Optional[str] = Field(default=None, description="Abbreviated team name")
    mascot: Optional[str] = Field(default=None, description="Team mascot")

    # Location
    city: Optional[str] = Field(default=None, description="City")
    state: Optional[str] = Field(default=None, description="State/Province")
    country: Optional[str] = Field(default=None, description="Country")
    region: Optional[str] = Field(default=None, description="Region (e.g., 'Northeast')")

    # School/Organization
    school_name: Optional[str] = Field(default=None, description="Associated school")
    organization: Optional[str] = Field(default=None, description="Parent organization")

    # Competition Info
    level: TeamLevel = Field(default=TeamLevel.UNKNOWN, description="Competition level")
    league: Optional[str] = Field(default=None, description="League name")
    conference: Optional[str] = Field(default=None, description="Conference/Division")
    season: Optional[str] = Field(default=None, description="Season (e.g., '2024-25')")

    # Coaching
    head_coach: Optional[str] = Field(default=None, description="Head coach name")
    assistant_coaches: Optional[list[str]] = Field(
        default=None, description="Assistant coaches"
    )

    # Contact & Media
    website: Optional[str] = Field(default=None, description="Team website")
    twitter_handle: Optional[str] = Field(default=None, description="Twitter/X handle")
    team_logo_url: Optional[str] = Field(default=None, description="Team logo URL")
    team_page_url: Optional[str] = Field(default=None, description="Team page URL")

    # Record (when available)
    wins: Optional[int] = Field(default=None, ge=0, description="Season wins")
    losses: Optional[int] = Field(default=None, ge=0, description="Season losses")

    # Metadata
    data_source: DataSource = Field(description="Where this data came from")

    @property
    def record(self) -> Optional[str]:
        """Get win-loss record as string."""
        if self.wins is None or self.losses is None:
            return None
        return f"{self.wins}-{self.losses}"

    @property
    def win_percentage(self) -> Optional[float]:
        """Calculate win percentage."""
        if self.wins is None or self.losses is None:
            return None
        total_games = self.wins + self.losses
        if total_games == 0:
            return None
        return self.wins / total_games

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "psal_lincoln_2024",
                "team_name": "Lincoln High School",
                "short_name": "Lincoln",
                "mascot": "Lions",
                "city": "Brooklyn",
                "state": "NY",
                "country": "USA",
                "school_name": "Abraham Lincoln High School",
                "level": "high_school_varsity",
                "league": "PSAL",
                "conference": "Brooklyn AA",
                "season": "2024-25",
                "head_coach": "John Doe",
                "wins": 18,
                "losses": 5,
                "team_page_url": "https://www.psal.org/teams/lincoln",
                "data_source": {
                    "source_type": "psal",
                    "source_name": "NYC PSAL",
                    "region": "us",
                    "quality_flag": "complete",
                },
            }
        }


class TeamStandings(BaseModel):
    """
    Team standings within a league/conference.

    Used for leaderboards and rankings.
    """

    team: Team = Field(description="Team information")
    rank: Optional[int] = Field(default=None, ge=1, description="Current rank")
    wins: int = Field(ge=0, description="Total wins")
    losses: int = Field(ge=0, description="Total losses")
    win_percentage: float = Field(ge=0.0, le=1.0, description="Win percentage")
    games_played: int = Field(ge=0, description="Games played")
    games_remaining: Optional[int] = Field(default=None, ge=0, description="Games remaining")
    streak: Optional[str] = Field(default=None, description="Current streak (e.g., 'W5', 'L2')")
    conference_wins: Optional[int] = Field(default=None, ge=0, description="Conference wins")
    conference_losses: Optional[int] = Field(default=None, ge=0, description="Conference losses")
    home_record: Optional[str] = Field(default=None, description="Home record")
    away_record: Optional[str] = Field(default=None, description="Away record")
    points_for: Optional[float] = Field(default=None, ge=0, description="Average points scored")
    points_against: Optional[float] = Field(
        default=None, ge=0, description="Average points allowed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "team": {"team_id": "eybl_team_1", "team_name": "Team Takeover"},
                "rank": 1,
                "wins": 12,
                "losses": 2,
                "win_percentage": 0.857,
                "games_played": 14,
                "games_remaining": 4,
                "streak": "W5",
                "points_for": 78.5,
                "points_against": 68.2,
            }
        }
