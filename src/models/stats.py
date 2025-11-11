"""
Statistics Models

Defines comprehensive basketball statistics models with detailed metrics.
"""

from typing import Optional

from pydantic import BaseModel, Field, computed_field


class BaseStats(BaseModel):
    """
    Base statistics that are common to most basketball stat sheets.

    This includes all standard box score stats.
    """

    # Minutes
    minutes_played: Optional[float] = Field(default=None, ge=0, description="Minutes played")

    # Scoring
    points: Optional[int] = Field(default=None, ge=0, description="Points scored")
    field_goals_made: Optional[int] = Field(default=None, ge=0, description="Field goals made")
    field_goals_attempted: Optional[int] = Field(
        default=None, ge=0, description="Field goals attempted"
    )
    three_pointers_made: Optional[int] = Field(default=None, ge=0, description="3-pointers made")
    three_pointers_attempted: Optional[int] = Field(
        default=None, ge=0, description="3-pointers attempted"
    )
    free_throws_made: Optional[int] = Field(default=None, ge=0, description="Free throws made")
    free_throws_attempted: Optional[int] = Field(
        default=None, ge=0, description="Free throws attempted"
    )

    # Rebounds
    offensive_rebounds: Optional[int] = Field(
        default=None, ge=0, description="Offensive rebounds"
    )
    defensive_rebounds: Optional[int] = Field(
        default=None, ge=0, description="Defensive rebounds"
    )
    total_rebounds: Optional[int] = Field(default=None, ge=0, description="Total rebounds")

    # Assists & Turnovers
    assists: Optional[int] = Field(default=None, ge=0, description="Assists")
    turnovers: Optional[int] = Field(default=None, ge=0, description="Turnovers")

    # Defense
    steals: Optional[int] = Field(default=None, ge=0, description="Steals")
    blocks: Optional[int] = Field(default=None, ge=0, description="Blocks")

    # Fouls
    personal_fouls: Optional[int] = Field(default=None, ge=0, description="Personal fouls")
    technical_fouls: Optional[int] = Field(default=None, ge=0, description="Technical fouls")

    # Advanced Stats (when available)
    plus_minus: Optional[int] = Field(default=None, description="Plus/minus")

    @computed_field
    @property
    def field_goal_percentage(self) -> Optional[float]:
        """Calculate field goal percentage."""
        if self.field_goals_attempted is None or self.field_goals_attempted == 0:
            return None
        if self.field_goals_made is None:
            return None
        return round((self.field_goals_made / self.field_goals_attempted) * 100, 1)

    @computed_field
    @property
    def three_point_percentage(self) -> Optional[float]:
        """Calculate 3-point percentage."""
        if self.three_pointers_attempted is None or self.three_pointers_attempted == 0:
            return None
        if self.three_pointers_made is None:
            return None
        return round((self.three_pointers_made / self.three_pointers_attempted) * 100, 1)

    @computed_field
    @property
    def free_throw_percentage(self) -> Optional[float]:
        """Calculate free throw percentage."""
        if self.free_throws_attempted is None or self.free_throws_attempted == 0:
            return None
        if self.free_throws_made is None:
            return None
        return round((self.free_throws_made / self.free_throws_attempted) * 100, 1)

    @computed_field
    @property
    def two_pointers_made(self) -> Optional[int]:
        """Calculate 2-pointers made."""
        if self.field_goals_made is None or self.three_pointers_made is None:
            return None
        return self.field_goals_made - self.three_pointers_made

    @computed_field
    @property
    def two_pointers_attempted(self) -> Optional[int]:
        """Calculate 2-pointers attempted."""
        if self.field_goals_attempted is None or self.three_pointers_attempted is None:
            return None
        return self.field_goals_attempted - self.three_pointers_attempted

    @computed_field
    @property
    def assist_to_turnover_ratio(self) -> Optional[float]:
        """Calculate assist-to-turnover ratio."""
        if self.assists is None or self.turnovers is None or self.turnovers == 0:
            return None
        return round(self.assists / self.turnovers, 2)


class PlayerGameStats(BaseStats):
    """
    Player statistics for a single game.

    Extends BaseStats with player and game identifiers.
    """

    # Identifiers
    player_id: str = Field(description="Player ID")
    player_name: str = Field(description="Player name")
    game_id: str = Field(description="Game ID")
    team_id: str = Field(description="Team ID")
    opponent_team_id: str = Field(description="Opponent team ID")

    # Game Context
    is_starter: Optional[bool] = Field(default=None, description="Whether player started")
    jersey_number: Optional[int] = Field(default=None, ge=0, le=99, description="Jersey number")
    position: Optional[str] = Field(default=None, description="Position played")

    # Additional Game-Specific Stats
    dunks: Optional[int] = Field(default=None, ge=0, description="Dunks")
    double_double: Optional[bool] = Field(default=None, description="Achieved double-double")
    triple_double: Optional[bool] = Field(default=None, description="Achieved triple-double")

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "eybl_12345",
                "player_name": "John Smith",
                "game_id": "eybl_game_001",
                "team_id": "eybl_team1",
                "opponent_team_id": "eybl_team2",
                "minutes_played": 28.5,
                "points": 24,
                "field_goals_made": 9,
                "field_goals_attempted": 18,
                "three_pointers_made": 3,
                "three_pointers_attempted": 7,
                "free_throws_made": 3,
                "free_throws_attempted": 4,
                "offensive_rebounds": 2,
                "defensive_rebounds": 5,
                "total_rebounds": 7,
                "assists": 6,
                "turnovers": 2,
                "steals": 3,
                "blocks": 1,
                "personal_fouls": 2,
                "plus_minus": 12,
                "is_starter": True,
                "jersey_number": 23,
                "position": "SG",
            }
        }


class PlayerSeasonStats(BaseStats):
    """
    Player statistics aggregated over a season.

    Includes both totals and averages.
    """

    # Identifiers
    player_id: str = Field(description="Player ID")
    player_name: str = Field(description="Player name")
    team_id: str = Field(description="Team ID")
    season: str = Field(description="Season (e.g., '2024-25')")
    league: Optional[str] = Field(default=None, description="League name")

    # Games Played
    games_played: int = Field(ge=0, description="Games played")
    games_started: Optional[int] = Field(default=None, ge=0, description="Games started")

    # Per Game Averages (calculated from totals)
    points_per_game: Optional[float] = Field(default=None, ge=0, description="Points per game")
    rebounds_per_game: Optional[float] = Field(default=None, ge=0, description="Rebounds per game")
    assists_per_game: Optional[float] = Field(default=None, ge=0, description="Assists per game")
    steals_per_game: Optional[float] = Field(default=None, ge=0, description="Steals per game")
    blocks_per_game: Optional[float] = Field(default=None, ge=0, description="Blocks per game")
    minutes_per_game: Optional[float] = Field(
        default=None, ge=0, description="Minutes per game"
    )

    # High Game Values
    high_points: Optional[int] = Field(default=None, ge=0, description="Highest points in a game")
    high_rebounds: Optional[int] = Field(
        default=None, ge=0, description="Highest rebounds in a game"
    )
    high_assists: Optional[int] = Field(
        default=None, ge=0, description="Highest assists in a game"
    )

    # Additional Season Stats
    double_doubles: Optional[int] = Field(default=None, ge=0, description="Number of double-doubles")
    triple_doubles: Optional[int] = Field(
        default=None, ge=0, description="Number of triple-doubles"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "player_id": "eybl_12345",
                "player_name": "John Smith",
                "team_id": "eybl_team1",
                "season": "2024-25",
                "league": "Nike EYBL",
                "games_played": 20,
                "games_started": 18,
                "points": 480,
                "points_per_game": 24.0,
                "field_goals_made": 180,
                "field_goals_attempted": 360,
                "three_pointers_made": 60,
                "three_pointers_attempted": 140,
                "total_rebounds": 140,
                "rebounds_per_game": 7.0,
                "assists": 120,
                "assists_per_game": 6.0,
                "steals": 40,
                "steals_per_game": 2.0,
                "high_points": 32,
                "high_rebounds": 12,
                "high_assists": 10,
                "double_doubles": 8,
            }
        }


class TeamGameStats(BaseStats):
    """
    Team statistics for a single game.

    Aggregates all team stats including player stats.
    """

    # Identifiers
    team_id: str = Field(description="Team ID")
    team_name: str = Field(description="Team name")
    game_id: str = Field(description="Game ID")
    opponent_team_id: str = Field(description="Opponent team ID")

    # Team-Specific Stats
    bench_points: Optional[int] = Field(default=None, ge=0, description="Points from bench")
    points_in_paint: Optional[int] = Field(default=None, ge=0, description="Points in the paint")
    fast_break_points: Optional[int] = Field(
        default=None, ge=0, description="Fast break points"
    )
    second_chance_points: Optional[int] = Field(
        default=None, ge=0, description="Second chance points"
    )
    points_off_turnovers: Optional[int] = Field(
        default=None, ge=0, description="Points off turnovers"
    )

    # Shooting Efficiency
    effective_field_goal_percentage: Optional[float] = Field(
        default=None, ge=0, le=100, description="Effective FG%"
    )
    true_shooting_percentage: Optional[float] = Field(
        default=None, ge=0, le=100, description="True shooting %"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": "eybl_team1",
                "team_name": "Team Takeover",
                "game_id": "eybl_game_001",
                "opponent_team_id": "eybl_team2",
                "points": 82,
                "field_goals_made": 30,
                "field_goals_attempted": 65,
                "three_pointers_made": 8,
                "three_pointers_attempted": 20,
                "free_throws_made": 14,
                "free_throws_attempted": 18,
                "total_rebounds": 38,
                "assists": 18,
                "turnovers": 12,
                "steals": 8,
                "blocks": 4,
                "bench_points": 22,
                "points_in_paint": 38,
                "fast_break_points": 16,
            }
        }


class LeaderboardEntry(BaseModel):
    """
    Entry in a statistical leaderboard.

    Used for ranking players by specific stats.
    """

    rank: int = Field(ge=1, description="Rank position")
    player_id: str = Field(description="Player ID")
    player_name: str = Field(description="Player name")
    team_name: Optional[str] = Field(default=None, description="Team name")
    stat_value: float = Field(description="Statistical value")
    stat_name: str = Field(description="Stat category name")
    games_played: Optional[int] = Field(default=None, ge=0, description="Games played")
    season: Optional[str] = Field(default=None, description="Season")

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "player_id": "eybl_12345",
                "player_name": "John Smith",
                "team_name": "Team Takeover",
                "stat_value": 24.5,
                "stat_name": "Points Per Game",
                "games_played": 20,
                "season": "2024-25",
            }
        }
