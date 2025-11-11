"""
Game Models

Defines game and game statistics data structures.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from .source import DataSource


class GameStatus(str, Enum):
    """Game status."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    FINAL = "final"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    FORFEIT = "forfeit"


class GameType(str, Enum):
    """Type of game."""

    REGULAR_SEASON = "regular_season"
    CONFERENCE = "conference"
    TOURNAMENT = "tournament"
    PLAYOFF = "playoff"
    CHAMPIONSHIP = "championship"
    SCRIMMAGE = "scrimmage"
    SHOWCASE = "showcase"
    UNKNOWN = "unknown"


class Game(BaseModel):
    """
    Comprehensive game data model.

    Represents a single basketball game with all available details.
    """

    # Identity
    game_id: str = Field(description="Unique game identifier")

    # Teams
    home_team_id: str = Field(description="Home team ID")
    away_team_id: str = Field(description="Away team ID")
    home_team_name: str = Field(description="Home team name")
    away_team_name: str = Field(description="Away team name")

    # Score
    home_score: Optional[int] = Field(default=None, ge=0, description="Home team score")
    away_score: Optional[int] = Field(default=None, ge=0, description="Away team score")

    # Status & Timing
    status: GameStatus = Field(description="Game status")
    game_date: datetime = Field(description="Game date and time")
    game_type: GameType = Field(default=GameType.UNKNOWN, description="Type of game")

    # Location
    venue_name: Optional[str] = Field(default=None, description="Venue name")
    venue_city: Optional[str] = Field(default=None, description="Venue city")
    venue_state: Optional[str] = Field(default=None, description="Venue state")

    # Competition
    league: Optional[str] = Field(default=None, description="League name")
    tournament: Optional[str] = Field(default=None, description="Tournament name")
    round: Optional[str] = Field(default=None, description="Tournament round")
    season: Optional[str] = Field(default=None, description="Season")

    # Additional Game Info
    attendance: Optional[int] = Field(default=None, ge=0, description="Attendance")
    officials: Optional[list[str]] = Field(default=None, description="Game officials/referees")

    # Overtime
    overtime_periods: Optional[int] = Field(
        default=None, ge=0, description="Number of overtime periods"
    )

    # Quarter/Half Scores (when available)
    home_q1: Optional[int] = Field(default=None, ge=0, description="Home Q1 score")
    home_q2: Optional[int] = Field(default=None, ge=0, description="Home Q2 score")
    home_q3: Optional[int] = Field(default=None, ge=0, description="Home Q3 score")
    home_q4: Optional[int] = Field(default=None, ge=0, description="Home Q4 score")
    away_q1: Optional[int] = Field(default=None, ge=0, description="Away Q1 score")
    away_q2: Optional[int] = Field(default=None, ge=0, description="Away Q2 score")
    away_q3: Optional[int] = Field(default=None, ge=0, description="Away Q3 score")
    away_q4: Optional[int] = Field(default=None, ge=0, description="Away Q4 score")

    # Media
    box_score_url: Optional[str] = Field(default=None, description="Box score URL")
    recap_url: Optional[str] = Field(default=None, description="Game recap URL")
    video_url: Optional[str] = Field(default=None, description="Game video URL")

    # Metadata
    data_source: DataSource = Field(description="Where this data came from")
    has_player_stats: bool = Field(default=False, description="Whether player stats available")
    has_team_stats: bool = Field(default=False, description="Whether team stats available")

    @property
    def winner_team_id(self) -> Optional[str]:
        """Get winning team ID."""
        if self.status != GameStatus.FINAL or self.home_score is None or self.away_score is None:
            return None
        if self.home_score > self.away_score:
            return self.home_team_id
        elif self.away_score > self.home_score:
            return self.away_team_id
        return None  # Tie (shouldn't happen in basketball)

    @property
    def point_differential(self) -> Optional[int]:
        """Get point differential (home - away)."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score - self.away_score

    @property
    def total_points(self) -> Optional[int]:
        """Get total points scored."""
        if self.home_score is None or self.away_score is None:
            return None
        return self.home_score + self.away_score

    @field_validator("away_score", "home_score")
    @classmethod
    def validate_score_with_status(cls, v: Optional[int], info) -> Optional[int]:
        """Validate that scores are present for completed games."""
        status = info.data.get("status")
        if status == GameStatus.FINAL and v is None:
            # Allow None for final games if data is incomplete
            # We'll flag this with data quality
            pass
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "game_id": "eybl_20251025_team1_team2",
                "home_team_id": "eybl_team1",
                "away_team_id": "eybl_team2",
                "home_team_name": "Team Takeover",
                "away_team_name": "Oakland Soldiers",
                "home_score": 82,
                "away_score": 76,
                "status": "final",
                "game_date": "2025-10-25T19:00:00Z",
                "game_type": "regular_season",
                "venue_name": "Nike World Headquarters",
                "venue_city": "Beaverton",
                "venue_state": "OR",
                "league": "Nike EYBL",
                "season": "2024-25",
                "home_q1": 18,
                "home_q2": 22,
                "home_q3": 20,
                "home_q4": 22,
                "away_q1": 20,
                "away_q2": 18,
                "away_q3": 19,
                "away_q4": 19,
                "box_score_url": "https://nikeeyb.com/games/12345/boxscore",
                "has_player_stats": True,
                "has_team_stats": True,
                "data_source": {
                    "source_type": "eybl",
                    "source_name": "Nike EYBL",
                    "region": "us",
                    "quality_flag": "complete",
                },
            }
        }


class GameSchedule(BaseModel):
    """
    Simplified game model for schedules.

    Used when we only need basic game info without stats.
    """

    game_id: str = Field(description="Game ID")
    home_team_name: str = Field(description="Home team")
    away_team_name: str = Field(description="Away team")
    game_date: datetime = Field(description="Game date/time")
    status: GameStatus = Field(description="Status")
    venue_name: Optional[str] = Field(default=None, description="Venue")
    game_url: Optional[str] = Field(default=None, description="Game page URL")
