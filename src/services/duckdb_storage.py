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

        # Recruiting ranks table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS recruiting_ranks (
                rank_id VARCHAR PRIMARY KEY,
                player_id VARCHAR NOT NULL,
                player_name VARCHAR NOT NULL,
                rank_national INTEGER,
                rank_position INTEGER,
                rank_state INTEGER,
                stars INTEGER CHECK (stars >= 3 AND stars <= 5),
                rating DOUBLE CHECK (rating >= 0.0 AND rating <= 1.0),
                service VARCHAR NOT NULL,
                class_year INTEGER NOT NULL CHECK (class_year >= 2020 AND class_year <= 2035),
                position VARCHAR,
                height VARCHAR,
                weight INTEGER,
                school VARCHAR,
                city VARCHAR,
                state VARCHAR,
                committed_to VARCHAR,
                commitment_date DATE,
                profile_url VARCHAR,
                source_type VARCHAR NOT NULL,
                retrieved_at TIMESTAMP NOT NULL,
                quality_flag VARCHAR,
                UNIQUE(player_id, service, class_year)
            )
        """)

        # College offers table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS college_offers (
                offer_id VARCHAR PRIMARY KEY,
                player_id VARCHAR NOT NULL,
                player_name VARCHAR NOT NULL,
                college VARCHAR NOT NULL,
                conference VARCHAR,
                conference_level VARCHAR,
                offer_date DATE,
                offer_status VARCHAR NOT NULL,
                commitment_date DATE,
                decommitment_date DATE,
                recruited_by VARCHAR,
                notes VARCHAR,
                source_type VARCHAR NOT NULL,
                retrieved_at TIMESTAMP NOT NULL,
                quality_flag VARCHAR,
                UNIQUE(player_id, college, offer_date)
            )
        """)

        # Recruiting predictions table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS recruiting_predictions (
                prediction_id VARCHAR PRIMARY KEY,
                player_id VARCHAR NOT NULL,
                player_name VARCHAR NOT NULL,
                predicted_college VARCHAR NOT NULL,
                predictor_name VARCHAR NOT NULL,
                predictor_org VARCHAR,
                prediction_date DATE NOT NULL,
                confidence_level VARCHAR,
                confidence_score DOUBLE CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
                prediction_type VARCHAR,
                notes VARCHAR,
                source_type VARCHAR NOT NULL,
                retrieved_at TIMESTAMP NOT NULL,
                quality_flag VARCHAR,
                UNIQUE(player_id, predicted_college, predictor_name, prediction_date)
            )
        """)

        # ======================================================================
        # NEW TABLES (Enhancement 10, Step 6): Historical Snapshots & Player Vectors
        # ======================================================================

        # Historical snapshots table: Multi-season tracking
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS historical_snapshots (
                snapshot_id VARCHAR PRIMARY KEY,
                player_uid VARCHAR NOT NULL,
                snapshot_date DATE NOT NULL,
                season VARCHAR,
                grad_year INTEGER,

                -- Bio snapshot
                height INTEGER,
                weight INTEGER,
                position VARCHAR,
                birth_date DATE,

                -- Recruiting snapshot
                composite_247_rating DOUBLE,
                stars_247 INTEGER,
                power_6_offer_count INTEGER,
                total_offer_count INTEGER,

                -- Performance snapshot
                ppg DOUBLE,
                rpg DOUBLE,
                apg DOUBLE,
                ts_pct DOUBLE,
                efg_pct DOUBLE,
                ato_ratio DOUBLE,

                -- Context
                school_name VARCHAR,
                state VARCHAR,
                league VARCHAR,
                competition_level VARCHAR,

                source_type VARCHAR NOT NULL,
                retrieved_at TIMESTAMP NOT NULL,

                UNIQUE(player_uid, snapshot_date, season)
            )
        """)

        # Player vectors table: For similarity searches
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS player_vectors (
                vector_id VARCHAR PRIMARY KEY,
                player_uid VARCHAR NOT NULL,
                season VARCHAR NOT NULL,

                -- 12-dimensional normalized vector for similarity
                ppg_per40_norm DOUBLE,
                rpg_per40_norm DOUBLE,
                apg_per40_norm DOUBLE,
                spg_per40_norm DOUBLE,
                bpg_per40_norm DOUBLE,
                ts_pct_norm DOUBLE,
                efg_pct_norm DOUBLE,
                ato_ratio_norm DOUBLE,
                height_norm DOUBLE,
                weight_norm DOUBLE,
                age_for_grade_norm DOUBLE,
                mpg_norm DOUBLE,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                UNIQUE(player_uid, season)
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

        # Recruiting table indexes
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recruiting_ranks_player ON recruiting_ranks(player_id, class_year)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recruiting_ranks_national ON recruiting_ranks(rank_national, class_year)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_college_offers_player ON college_offers(player_id, offer_status)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_recruiting_predictions_player ON recruiting_predictions(player_id, prediction_date)"
        )

        # Historical tables indexes (NEW - Enhancement 10, Step 6)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historical_snapshots_player ON historical_snapshots(player_uid, snapshot_date)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_historical_snapshots_season ON historical_snapshots(season, grad_year)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_player_vectors_player ON player_vectors(player_uid, season)"
        )

        logger.info("DuckDB schema initialized with 9 tables (4 stats + 3 recruiting + 2 historical) and indexes")

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

    async def store_recruiting_ranks(self, ranks: list) -> int:
        """
        Store recruiting rankings in DuckDB.

        Args:
            ranks: List of RecruitingRank objects

        Returns:
            Number of ranks stored
        """
        if not self.conn or not ranks:
            return 0

        try:
            data = []
            for rank in ranks:
                # Create unique rank_id
                rank_id = f"{rank.player_id}_{rank.service.value}_{rank.class_year}"

                data.append(
                    {
                        "rank_id": rank_id,
                        "player_id": rank.player_id,
                        "player_name": rank.player_name,
                        "rank_national": rank.rank_national,
                        "rank_position": rank.rank_position,
                        "rank_state": rank.rank_state,
                        "stars": rank.stars,
                        "rating": rank.rating,
                        "service": rank.service.value,
                        "class_year": rank.class_year,
                        "position": rank.position.value if rank.position else None,
                        "height": rank.height,
                        "weight": rank.weight,
                        "school": rank.school,
                        "city": rank.city,
                        "state": rank.state,
                        "committed_to": rank.committed_to,
                        "commitment_date": rank.commitment_date,
                        "profile_url": rank.profile_url,
                        "source_type": rank.data_source.source_type.value,
                        "retrieved_at": rank.data_source.retrieved_at,
                        "quality_flag": rank.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)
            self.conn.execute("INSERT OR REPLACE INTO recruiting_ranks SELECT * FROM df")

            logger.info(f"Stored {len(ranks)} recruiting ranks in DuckDB")
            return len(ranks)

        except Exception as e:
            logger.error("Failed to store recruiting ranks in DuckDB", error=str(e))
            return 0

    async def store_college_offers(self, offers: list) -> int:
        """
        Store college offers in DuckDB.

        Args:
            offers: List of CollegeOffer objects

        Returns:
            Number of offers stored
        """
        if not self.conn or not offers:
            return 0

        try:
            data = []
            for offer in offers:
                # Create unique offer_id
                offer_date_str = offer.offer_date.isoformat() if offer.offer_date else "unknown"
                offer_id = f"{offer.player_id}_{offer.college}_{offer_date_str}"

                data.append(
                    {
                        "offer_id": offer_id,
                        "player_id": offer.player_id,
                        "player_name": offer.player_name,
                        "college": offer.college,
                        "conference": offer.conference,
                        "conference_level": offer.conference_level.value if offer.conference_level else None,
                        "offer_date": offer.offer_date,
                        "offer_status": offer.status.value,
                        "commitment_date": offer.commitment_date,
                        "decommitment_date": offer.decommitment_date,
                        "recruited_by": offer.recruited_by,
                        "notes": offer.notes,
                        "source_type": offer.data_source.source_type.value,
                        "retrieved_at": offer.data_source.retrieved_at,
                        "quality_flag": offer.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)
            self.conn.execute("INSERT OR REPLACE INTO college_offers SELECT * FROM df")

            logger.info(f"Stored {len(offers)} college offers in DuckDB")
            return len(offers)

        except Exception as e:
            logger.error("Failed to store college offers in DuckDB", error=str(e))
            return 0

    async def store_recruiting_predictions(self, predictions: list) -> int:
        """
        Store recruiting predictions in DuckDB.

        Args:
            predictions: List of RecruitingPrediction objects

        Returns:
            Number of predictions stored
        """
        if not self.conn or not predictions:
            return 0

        try:
            data = []
            for pred in predictions:
                # Create unique prediction_id
                pred_date_str = pred.prediction_date.isoformat() if pred.prediction_date else "unknown"
                prediction_id = f"{pred.player_id}_{pred.predicted_college}_{pred.predictor_name}_{pred_date_str}"

                data.append(
                    {
                        "prediction_id": prediction_id,
                        "player_id": pred.player_id,
                        "player_name": pred.player_name,
                        "predicted_college": pred.predicted_college,
                        "predictor_name": pred.predictor_name,
                        "predictor_org": pred.predictor_org,
                        "prediction_date": pred.prediction_date,
                        "confidence_level": pred.confidence_level,
                        "confidence_score": pred.confidence_score,
                        "prediction_type": pred.prediction_type,
                        "notes": pred.notes,
                        "source_type": pred.data_source.source_type.value,
                        "retrieved_at": pred.data_source.retrieved_at,
                        "quality_flag": pred.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)
            self.conn.execute("INSERT OR REPLACE INTO recruiting_predictions SELECT * FROM df")

            logger.info(f"Stored {len(predictions)} recruiting predictions in DuckDB")
            return len(predictions)

        except Exception as e:
            logger.error("Failed to store recruiting predictions in DuckDB", error=str(e))
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

    def export_eybl_from_duckdb(
        self,
        season: Optional[str] = None,
        grad_year: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Export EYBL player stats from DuckDB for dataset building.

        Returns DataFrame with EYBL stats ready for merging with HS datasets.
        Includes player_uid for identity resolution.

        Args:
            season: Filter by season (e.g., "2024")
            grad_year: Filter by graduation year (if available in data)

        Returns:
            DataFrame with EYBL stats
        """
        if not self.conn:
            logger.warning("DuckDB not initialized, returning empty DataFrame")
            return pd.DataFrame()

        query = """
            SELECT
                player_id as player_uid,
                player_name,
                season,
                games_played,
                points_per_game,
                rebounds_per_game,
                assists_per_game,
                steals_per_game,
                blocks_per_game,
                field_goal_percentage,
                three_point_percentage,
                free_throw_percentage,
                team_id,
                retrieved_at
            FROM player_season_stats
            WHERE source_type = 'eybl'
        """

        params = []

        if season:
            query += " AND season = ?"
            params.append(season)

        query += " ORDER BY points_per_game DESC"

        try:
            df = self.conn.execute(query, params).fetchdf()
            logger.info(f"Exported {len(df)} EYBL player season records from DuckDB")
            return df
        except Exception as e:
            logger.error("Failed to export EYBL data from DuckDB", error=str(e))
            return pd.DataFrame()

    def export_recruiting_from_duckdb(
        self,
        class_year: Optional[int] = None,
        min_stars: Optional[int] = None,
        service: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Export recruiting rankings from DuckDB for dataset building.

        Returns DataFrame with recruiting rankings ready for merging.

        Args:
            class_year: Filter by high school graduation year
            min_stars: Minimum star rating (3-5)
            service: Recruiting service filter (e.g., "247sports", "composite")

        Returns:
            DataFrame with recruiting rankings
        """
        if not self.conn:
            logger.warning("DuckDB not initialized, returning empty DataFrame")
            return pd.DataFrame()

        query = """
            SELECT
                player_id as player_uid,
                player_name,
                rank_national,
                rank_position,
                rank_state,
                stars,
                rating,
                service,
                class_year,
                position,
                height,
                weight,
                school,
                city,
                state,
                committed_to,
                commitment_date,
                profile_url,
                retrieved_at
            FROM recruiting_ranks
            WHERE 1=1
        """

        params = []

        if class_year:
            query += " AND class_year = ?"
            params.append(class_year)

        if min_stars:
            query += " AND stars >= ?"
            params.append(min_stars)

        if service:
            query += " AND service = ?"
            params.append(service)

        query += " ORDER BY rank_national ASC NULLS LAST"

        try:
            df = self.conn.execute(query, params).fetchdf()
            logger.info(
                f"Exported {len(df)} recruiting rankings from DuckDB",
                class_year=class_year,
                min_stars=min_stars
            )
            return df
        except Exception as e:
            logger.error("Failed to export recruiting data from DuckDB", error=str(e))
            return pd.DataFrame()

    def export_college_offers_from_duckdb(
        self,
        class_year: Optional[int] = None,
        min_conference_level: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Export college offers from DuckDB for dataset building.

        Returns DataFrame with college offers ready for aggregation.

        Args:
            class_year: Filter by graduation year (if joined with recruiting)
            min_conference_level: Minimum conference level (e.g., "power_6")

        Returns:
            DataFrame with college offers
        """
        if not self.conn:
            logger.warning("DuckDB not initialized, returning empty DataFrame")
            return pd.DataFrame()

        query = """
            SELECT
                player_id as player_uid,
                player_name,
                college,
                conference,
                conference_level,
                offer_date,
                offer_status,
                commitment_date,
                retrieved_at
            FROM college_offers
            WHERE 1=1
        """

        params = []

        if min_conference_level:
            query += " AND conference_level = ?"
            params.append(min_conference_level)

        query += " ORDER BY player_name, offer_date DESC"

        try:
            df = self.conn.execute(query, params).fetchdf()
            logger.info(f"Exported {len(df)} college offers from DuckDB")
            return df
        except Exception as e:
            logger.error("Failed to export college offers from DuckDB", error=str(e))
            return pd.DataFrame()

    def export_maxpreps_from_duckdb(
        self,
        season: Optional[str] = None,
        state: Optional[str] = None,
        min_ppg: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Export MaxPreps HS stats from DuckDB for dataset building.

        Returns DataFrame with HS stats ready for merging.

        Args:
            season: Filter by season (e.g., "2024")
            state: Filter by school state
            min_ppg: Minimum points per game filter

        Returns:
            DataFrame with MaxPreps stats
        """
        if not self.conn:
            logger.warning("DuckDB not initialized, returning empty DataFrame")
            return pd.DataFrame()

        # Need to join with players table to get school info
        query = """
            SELECT
                s.player_id as player_uid,
                s.player_name,
                s.season,
                s.games_played,
                s.points_per_game,
                s.rebounds_per_game,
                s.assists_per_game,
                s.steals_per_game,
                s.blocks_per_game,
                s.field_goals_made,
                s.field_goals_attempted,
                s.three_pointers_made,
                s.three_pointers_attempted,
                s.free_throws_made,
                s.free_throws_attempted,
                s.turnovers,
                s.minutes_played,
                p.school_name,
                p.school_state,
                p.grad_year,
                s.retrieved_at
            FROM player_season_stats s
            LEFT JOIN players p ON s.player_id = p.player_id AND s.source_type = p.source_type
            WHERE s.source_type = 'maxpreps'
        """

        params = []

        if season:
            query += " AND s.season = ?"
            params.append(season)

        if state:
            query += " AND p.school_state = ?"
            params.append(state)

        if min_ppg is not None:
            query += " AND s.points_per_game >= ?"
            params.append(min_ppg)

        query += " ORDER BY s.points_per_game DESC"

        try:
            df = self.conn.execute(query, params).fetchdf()
            logger.info(
                f"Exported {len(df)} MaxPreps player season records from DuckDB",
                season=season,
                state=state
            )
            return df
        except Exception as e:
            logger.error("Failed to export MaxPreps data from DuckDB", error=str(e))
            return pd.DataFrame()

    def get_dataset_sources_summary(
        self,
        class_year: Optional[int] = None
    ) -> Dict:
        """
        Get summary of available data sources for dataset building.

        Useful for understanding data coverage before building datasets.

        Args:
            class_year: Filter by graduation year

        Returns:
            Dictionary with counts per source
        """
        if not self.conn:
            return {}

        try:
            summary = {}

            # EYBL stats count
            eybl_query = "SELECT COUNT(*) FROM player_season_stats WHERE source_type = 'eybl'"
            summary['eybl_stats'] = self.conn.execute(eybl_query).fetchone()[0]

            # MaxPreps stats count
            mp_query = "SELECT COUNT(*) FROM player_season_stats WHERE source_type = 'maxpreps'"
            summary['maxpreps_stats'] = self.conn.execute(mp_query).fetchone()[0]

            # Recruiting rankings count
            if class_year:
                rec_query = f"SELECT COUNT(*) FROM recruiting_ranks WHERE class_year = {class_year}"
            else:
                rec_query = "SELECT COUNT(*) FROM recruiting_ranks"
            summary['recruiting_ranks'] = self.conn.execute(rec_query).fetchone()[0]

            # College offers count
            summary['college_offers'] = self.conn.execute("SELECT COUNT(*) FROM college_offers").fetchone()[0]

            # Unique players count
            summary['unique_players'] = self.conn.execute("SELECT COUNT(DISTINCT player_id) FROM players").fetchone()[0]

            logger.info("Dataset sources summary generated", summary=summary)
            return summary

        except Exception as e:
            logger.error("Failed to get dataset sources summary", error=str(e))
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
