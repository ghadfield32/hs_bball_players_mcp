"""
DuckDB Storage Service

Provides efficient analytical storage and querying using DuckDB.
Stores all scraped basketball data in columnar format for fast analytics.
"""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import duckdb
import pandas as pd

from ..config import get_settings
from ..models import Game, Player, PlayerSeasonStats, Team
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DuckDBStorage:
    """
    DuckDB-based analytical storage for basketball statistics.

    Provides efficient columnar storage and SQL-based querying for analytics.
    Uses DuckDB's zero-config, in-process analytical database.
    """

    def __init__(self):
        """Initialize DuckDB storage."""
        self.settings = get_settings()

        if not self.settings.duckdb_enabled:
            logger.warning("DuckDB is disabled in configuration")
            self.conn = None
            return

        # Create data directory if needed
        db_path = Path(self.settings.duckdb_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize DuckDB connection
        self.conn = duckdb.connect(str(db_path))

        # Configure DuckDB
        self.conn.execute(f"SET memory_limit='{self.settings.duckdb_memory_limit}'")
        self.conn.execute(f"SET threads={self.settings.duckdb_threads}")

        # Initialize schema
        self._initialize_schema()

        logger.info(
            "DuckDB storage initialized",
            path=str(db_path),
            memory_limit=self.settings.duckdb_memory_limit,
            threads=self.settings.duckdb_threads,
        )

    def _initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        if not self.conn:
            return

        # Players table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS players (
                player_id VARCHAR PRIMARY KEY,
                source_type VARCHAR NOT NULL,
                first_name VARCHAR,
                last_name VARCHAR,
                full_name VARCHAR NOT NULL,
                position VARCHAR,
                height_inches INTEGER,
                weight_lbs INTEGER,
                school_name VARCHAR,
                school_city VARCHAR,
                school_state VARCHAR,
                school_country VARCHAR,
                team_name VARCHAR,
                jersey_number INTEGER,
                grad_year INTEGER,
                birth_date DATE,
                level VARCHAR,
                profile_url VARCHAR,
                retrieved_at TIMESTAMP NOT NULL,
                quality_flag VARCHAR,
                UNIQUE(player_id, source_type)
            )
        """)

        # Teams table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id VARCHAR PRIMARY KEY,
                source_type VARCHAR NOT NULL,
                team_name VARCHAR NOT NULL,
                school_name VARCHAR,
                city VARCHAR,
                state VARCHAR,
                country VARCHAR,
                region VARCHAR,
                level VARCHAR,
                league VARCHAR,
                conference VARCHAR,
                season VARCHAR,
                wins INTEGER,
                losses INTEGER,
                head_coach VARCHAR,
                retrieved_at TIMESTAMP NOT NULL,
                quality_flag VARCHAR,
                UNIQUE(team_id, source_type, season)
            )
        """)

        # Player season stats table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS player_season_stats (
                stat_id VARCHAR PRIMARY KEY,
                player_id VARCHAR NOT NULL,
                player_name VARCHAR NOT NULL,
                team_id VARCHAR,
                source_type VARCHAR NOT NULL,
                season VARCHAR NOT NULL,
                league VARCHAR,
                games_played INTEGER,
                games_started INTEGER,
                minutes_played DOUBLE,
                points INTEGER,
                points_per_game DOUBLE,
                field_goals_made INTEGER,
                field_goals_attempted INTEGER,
                three_pointers_made INTEGER,
                three_pointers_attempted INTEGER,
                free_throws_made INTEGER,
                free_throws_attempted INTEGER,
                offensive_rebounds INTEGER,
                defensive_rebounds INTEGER,
                total_rebounds INTEGER,
                rebounds_per_game DOUBLE,
                assists INTEGER,
                assists_per_game DOUBLE,
                steals INTEGER,
                steals_per_game DOUBLE,
                blocks INTEGER,
                blocks_per_game DOUBLE,
                turnovers INTEGER,
                personal_fouls INTEGER,
                high_points INTEGER,
                high_rebounds INTEGER,
                high_assists INTEGER,
                double_doubles INTEGER,
                triple_doubles INTEGER,
                retrieved_at TIMESTAMP NOT NULL,
                UNIQUE(player_id, season, source_type)
            )
        """)

        # Games table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS games (
                game_id VARCHAR PRIMARY KEY,
                source_type VARCHAR NOT NULL,
                home_team_id VARCHAR NOT NULL,
                away_team_id VARCHAR NOT NULL,
                home_team_name VARCHAR NOT NULL,
                away_team_name VARCHAR NOT NULL,
                home_score INTEGER,
                away_score INTEGER,
                status VARCHAR NOT NULL,
                game_date TIMESTAMP NOT NULL,
                game_type VARCHAR,
                venue_name VARCHAR,
                venue_city VARCHAR,
                venue_state VARCHAR,
                league VARCHAR,
                tournament VARCHAR,
                season VARCHAR,
                attendance INTEGER,
                overtime_periods INTEGER,
                home_q1 INTEGER,
                home_q2 INTEGER,
                home_q3 INTEGER,
                home_q4 INTEGER,
                away_q1 INTEGER,
                away_q2 INTEGER,
                away_q3 INTEGER,
                away_q4 INTEGER,
                box_score_url VARCHAR,
                retrieved_at TIMESTAMP NOT NULL,
                UNIQUE(game_id, source_type)
            )
        """)

        # Create indexes for common queries
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_players_name ON players(full_name, source_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_players_school ON players(school_name, source_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_teams_name ON teams(team_name, source_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stats_player ON player_season_stats(player_id, season)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_games_date ON games(game_date, source_type)"
        )

        logger.info("DuckDB schema initialized with 4 tables and indexes")

    async def store_players(self, players: list[Player]) -> int:
        """
        Store players in DuckDB.

        Args:
            players: List of Player objects

        Returns:
            Number of players stored
        """
        if not self.conn or not players:
            return 0

        try:
            # Convert to DataFrame
            data = []
            for player in players:
                data.append(
                    {
                        "player_id": player.player_id,
                        "source_type": player.data_source.source_type.value,
                        "first_name": player.first_name,
                        "last_name": player.last_name,
                        "full_name": player.full_name,
                        "position": player.position.value if player.position else None,
                        "height_inches": player.height_inches,
                        "weight_lbs": player.weight_lbs,
                        "school_name": player.school_name,
                        "school_city": player.school_city,
                        "school_state": player.school_state,
                        "school_country": player.school_country,
                        "team_name": player.team_name,
                        "jersey_number": player.jersey_number,
                        "grad_year": player.grad_year,
                        "birth_date": player.birth_date,
                        "level": player.level.value,
                        "profile_url": player.profile_url,
                        "retrieved_at": player.data_source.retrieved_at,
                        "quality_flag": player.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)

            # Insert or replace
            self.conn.execute("INSERT OR REPLACE INTO players SELECT * FROM df")

            logger.info(f"Stored {len(players)} players in DuckDB")
            return len(players)

        except Exception as e:
            logger.error("Failed to store players in DuckDB", error=str(e))
            return 0

    async def store_teams(self, teams: list[Team]) -> int:
        """
        Store teams in DuckDB.

        Args:
            teams: List of Team objects

        Returns:
            Number of teams stored
        """
        if not self.conn or not teams:
            return 0

        try:
            data = []
            for team in teams:
                data.append(
                    {
                        "team_id": team.team_id,
                        "source_type": team.data_source.source_type.value,
                        "team_name": team.team_name,
                        "school_name": team.school_name,
                        "city": team.city,
                        "state": team.state,
                        "country": team.country,
                        "region": team.region,
                        "level": team.level.value,
                        "league": team.league,
                        "conference": team.conference,
                        "season": team.season,
                        "wins": team.wins,
                        "losses": team.losses,
                        "head_coach": team.head_coach,
                        "retrieved_at": team.data_source.retrieved_at,
                        "quality_flag": team.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)
            self.conn.execute("INSERT OR REPLACE INTO teams SELECT * FROM df")

            logger.info(f"Stored {len(teams)} teams in DuckDB")
            return len(teams)

        except Exception as e:
            logger.error("Failed to store teams in DuckDB", error=str(e))
            return 0

    async def store_player_stats(self, stats: list[PlayerSeasonStats]) -> int:
        """
        Store player season statistics in DuckDB.

        Args:
            stats: List of PlayerSeasonStats objects

        Returns:
            Number of stats records stored
        """
        if not self.conn or not stats:
            return 0

        try:
            data = []
            for stat in stats:
                # Create unique stat_id
                stat_id = f"{stat.player_id}_{stat.season}_{stat.league or 'unknown'}"

                data.append(
                    {
                        "stat_id": stat_id,
                        "player_id": stat.player_id,
                        "player_name": stat.player_name,
                        "team_id": stat.team_id,
                        "source_type": stat.player_id.split("_")[0],  # Extract from player_id
                        "season": stat.season,
                        "league": stat.league,
                        "games_played": stat.games_played,
                        "games_started": stat.games_started,
                        "minutes_played": stat.minutes_played,
                        "points": stat.points,
                        "points_per_game": stat.points_per_game,
                        "field_goals_made": stat.field_goals_made,
                        "field_goals_attempted": stat.field_goals_attempted,
                        "three_pointers_made": stat.three_pointers_made,
                        "three_pointers_attempted": stat.three_pointers_attempted,
                        "free_throws_made": stat.free_throws_made,
                        "free_throws_attempted": stat.free_throws_attempted,
                        "offensive_rebounds": stat.offensive_rebounds,
                        "defensive_rebounds": stat.defensive_rebounds,
                        "total_rebounds": stat.total_rebounds,
                        "rebounds_per_game": stat.rebounds_per_game,
                        "assists": stat.assists,
                        "assists_per_game": stat.assists_per_game,
                        "steals": stat.steals,
                        "steals_per_game": stat.steals_per_game,
                        "blocks": stat.blocks,
                        "blocks_per_game": stat.blocks_per_game,
                        "turnovers": stat.turnovers,
                        "personal_fouls": stat.personal_fouls,
                        "high_points": stat.high_points,
                        "high_rebounds": stat.high_rebounds,
                        "high_assists": stat.high_assists,
                        "double_doubles": stat.double_doubles,
                        "triple_doubles": stat.triple_doubles,
                        "retrieved_at": datetime.utcnow(),
                    }
                )

            df = pd.DataFrame(data)
            self.conn.execute("INSERT OR REPLACE INTO player_season_stats SELECT * FROM df")

            logger.info(f"Stored {len(stats)} player stats in DuckDB")
            return len(stats)

        except Exception as e:
            logger.error("Failed to store player stats in DuckDB", error=str(e))
            return 0

    def query_players(
        self,
        name: Optional[str] = None,
        school: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Query players from DuckDB.

        Args:
            name: Player name filter (partial match)
            school: School name filter (partial match)
            source: Source type filter
            limit: Maximum results

        Returns:
            DataFrame with query results
        """
        if not self.conn:
            return pd.DataFrame()

        query = "SELECT * FROM players WHERE 1=1"
        params = []

        if name:
            query += " AND full_name ILIKE ?"
            params.append(f"%{name}%")

        if school:
            query += " AND school_name ILIKE ?"
            params.append(f"%{school}%")

        if source:
            query += " AND source_type = ?"
            params.append(source)

        query += f" ORDER BY retrieved_at DESC LIMIT {limit}"

        try:
            result = self.conn.execute(query, params).fetchdf()
            logger.info(f"Query returned {len(result)} players")
            return result
        except Exception as e:
            logger.error("Failed to query players", error=str(e))
            return pd.DataFrame()

    def query_stats(
        self,
        player_name: Optional[str] = None,
        season: Optional[str] = None,
        min_ppg: Optional[float] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> pd.DataFrame:
        """
        Query player statistics from DuckDB.

        Args:
            player_name: Player name filter
            season: Season filter
            min_ppg: Minimum points per game
            source: Source type filter
            limit: Maximum results

        Returns:
            DataFrame with query results
        """
        if not self.conn:
            return pd.DataFrame()

        query = "SELECT * FROM player_season_stats WHERE 1=1"
        params = []

        if player_name:
            query += " AND player_name ILIKE ?"
            params.append(f"%{player_name}%")

        if season:
            query += " AND season = ?"
            params.append(season)

        if min_ppg is not None:
            query += " AND points_per_game >= ?"
            params.append(min_ppg)

        if source:
            query += " AND source_type = ?"
            params.append(source)

        query += f" ORDER BY points_per_game DESC LIMIT {limit}"

        try:
            result = self.conn.execute(query, params).fetchdf()
            logger.info(f"Query returned {len(result)} stat records")
            return result
        except Exception as e:
            logger.error("Failed to query stats", error=str(e))
            return pd.DataFrame()

    def get_leaderboard(
        self,
        stat: str = "points_per_game",
        season: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """
        Get statistical leaderboard from DuckDB.

        Args:
            stat: Stat column to rank by
            season: Season filter
            source: Source type filter
            limit: Maximum results

        Returns:
            DataFrame with leaderboard
        """
        if not self.conn:
            return pd.DataFrame()

        # Validate stat column exists
        valid_stats = [
            "points_per_game",
            "rebounds_per_game",
            "assists_per_game",
            "steals_per_game",
            "blocks_per_game",
            "points",
            "rebounds",
            "assists",
        ]

        if stat not in valid_stats:
            logger.warning(f"Invalid stat column: {stat}")
            return pd.DataFrame()

        query = f"""
            SELECT
                player_name,
                team_id,
                season,
                league,
                source_type,
                games_played,
                {stat},
                ROW_NUMBER() OVER (ORDER BY {stat} DESC) as rank
            FROM player_season_stats
            WHERE {stat} IS NOT NULL
        """

        params = []

        if season:
            query += " AND season = ?"
            params.append(season)

        if source:
            query += " AND source_type = ?"
            params.append(source)

        query += f" ORDER BY {stat} DESC LIMIT {limit}"

        try:
            result = self.conn.execute(query, params).fetchdf()
            logger.info(f"Leaderboard query returned {len(result)} results")
            return result
        except Exception as e:
            logger.error("Failed to get leaderboard", error=str(e))
            return pd.DataFrame()

    def get_analytics_summary(self) -> dict:
        """
        Get summary analytics from DuckDB.

        Returns:
            Dictionary with summary statistics
        """
        if not self.conn:
            return {}

        try:
            summary = {}

            # Player count by source
            result = self.conn.execute(
                "SELECT source_type, COUNT(*) as count FROM players GROUP BY source_type"
            ).fetchdf()
            summary["players_by_source"] = result.to_dict("records")

            # Team count by league
            result = self.conn.execute(
                "SELECT league, COUNT(*) as count FROM teams GROUP BY league"
            ).fetchdf()
            summary["teams_by_league"] = result.to_dict("records")

            # Stats by season
            result = self.conn.execute(
                "SELECT season, COUNT(*) as count FROM player_season_stats GROUP BY season"
            ).fetchdf()
            summary["stats_by_season"] = result.to_dict("records")

            # Total counts
            summary["total_players"] = self.conn.execute(
                "SELECT COUNT(*) FROM players"
            ).fetchone()[0]
            summary["total_teams"] = self.conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
            summary["total_stats"] = self.conn.execute(
                "SELECT COUNT(*) FROM player_season_stats"
            ).fetchone()[0]

            return summary

        except Exception as e:
            logger.error("Failed to get analytics summary", error=str(e))
            return {}

    def close(self) -> None:
        """Close DuckDB connection."""
        if self.conn:
            self.conn.close()
            logger.info("DuckDB connection closed")


# Global DuckDB storage instance
_duckdb_storage_instance: Optional[DuckDBStorage] = None


def get_duckdb_storage() -> DuckDBStorage:
    """
    Get global DuckDB storage instance.

    Returns:
        DuckDBStorage instance
    """
    global _duckdb_storage_instance
    if _duckdb_storage_instance is None:
        _duckdb_storage_instance = DuckDBStorage()
    return _duckdb_storage_instance
