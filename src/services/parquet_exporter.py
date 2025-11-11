"""
Parquet Export Utilities

Provides efficient data export to Parquet format with compression.
Parquet is a columnar storage format that provides excellent compression
and fast read performance for analytical queries.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ..config import get_settings
from ..models import Game, Player, PlayerSeasonStats, Team
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ParquetExporter:
    """
    Parquet file exporter for basketball statistics.

    Handles conversion of Pydantic models to Parquet files with
    optimal compression and schema preservation.
    """

    def __init__(self):
        """Initialize Parquet exporter."""
        self.settings = get_settings()

        # Create export directory
        self.export_dir = Path(self.settings.export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)

        # Subdirectories for different data types
        (self.export_dir / "players").mkdir(exist_ok=True)
        (self.export_dir / "teams").mkdir(exist_ok=True)
        (self.export_dir / "games").mkdir(exist_ok=True)
        (self.export_dir / "stats").mkdir(exist_ok=True)

        logger.info(
            "Parquet exporter initialized",
            export_dir=str(self.export_dir.absolute()),
            compression=self.settings.parquet_compression,
        )

    def _get_timestamp_suffix(self) -> str:
        """Get timestamp suffix for filenames."""
        return datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    async def export_players(
        self,
        players: list[Player],
        filename: Optional[str] = None,
        partition_by_source: bool = True,
    ) -> str:
        """
        Export players to Parquet file.

        Args:
            players: List of Player objects
            filename: Optional custom filename (without extension)
            partition_by_source: Whether to partition by data source

        Returns:
            Path to exported file
        """
        if not players:
            logger.warning("No players to export")
            return ""

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
                        "birth_date": player.birth_date.isoformat() if player.birth_date else None,
                        "level": player.level.value,
                        "profile_url": player.profile_url,
                        "retrieved_at": player.data_source.retrieved_at.isoformat(),
                        "quality_flag": player.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)

            # Generate filename
            if filename is None:
                filename = f"players_{self._get_timestamp_suffix()}"

            output_path = self.export_dir / "players" / f"{filename}.parquet"

            # Write Parquet file
            if partition_by_source and "source_type" in df.columns:
                # Partition by source for better organization
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(
                    table,
                    root_path=str(output_path.parent / filename),
                    partition_cols=["source_type"],
                    compression=self.settings.parquet_compression,
                )
                logger.info(
                    f"Exported {len(players)} players to partitioned Parquet",
                    path=str(output_path),
                )
            else:
                # Write single file
                table = pa.Table.from_pandas(df)
                pq.write_table(
                    table, str(output_path), compression=self.settings.parquet_compression
                )
                logger.info(
                    f"Exported {len(players)} players to Parquet",
                    path=str(output_path),
                    size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
                )

            return str(output_path)

        except Exception as e:
            logger.error("Failed to export players to Parquet", error=str(e))
            return ""

    async def export_teams(
        self, teams: list[Team], filename: Optional[str] = None
    ) -> str:
        """
        Export teams to Parquet file.

        Args:
            teams: List of Team objects
            filename: Optional custom filename

        Returns:
            Path to exported file
        """
        if not teams:
            logger.warning("No teams to export")
            return ""

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
                        "level": team.level.value,
                        "league": team.league,
                        "conference": team.conference,
                        "season": team.season,
                        "wins": team.wins,
                        "losses": team.losses,
                        "win_percentage": team.win_percentage,
                        "head_coach": team.head_coach,
                        "retrieved_at": team.data_source.retrieved_at.isoformat(),
                        "quality_flag": team.data_source.quality_flag.value,
                    }
                )

            df = pd.DataFrame(data)

            if filename is None:
                filename = f"teams_{self._get_timestamp_suffix()}"

            output_path = self.export_dir / "teams" / f"{filename}.parquet"

            table = pa.Table.from_pandas(df)
            pq.write_table(
                table, str(output_path), compression=self.settings.parquet_compression
            )

            logger.info(
                f"Exported {len(teams)} teams to Parquet",
                path=str(output_path),
                size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
            )

            return str(output_path)

        except Exception as e:
            logger.error("Failed to export teams to Parquet", error=str(e))
            return ""

    async def export_player_stats(
        self, stats: list[PlayerSeasonStats], filename: Optional[str] = None
    ) -> str:
        """
        Export player statistics to Parquet file.

        Args:
            stats: List of PlayerSeasonStats objects
            filename: Optional custom filename

        Returns:
            Path to exported file
        """
        if not stats:
            logger.warning("No stats to export")
            return ""

        try:
            data = []
            for stat in stats:
                data.append(
                    {
                        "player_id": stat.player_id,
                        "player_name": stat.player_name,
                        "team_id": stat.team_id,
                        "season": stat.season,
                        "league": stat.league,
                        "games_played": stat.games_played,
                        "games_started": stat.games_started,
                        "minutes_played": stat.minutes_played,
                        "points": stat.points,
                        "points_per_game": stat.points_per_game,
                        "field_goals_made": stat.field_goals_made,
                        "field_goals_attempted": stat.field_goals_attempted,
                        "field_goal_percentage": stat.field_goal_percentage,
                        "three_pointers_made": stat.three_pointers_made,
                        "three_pointers_attempted": stat.three_pointers_attempted,
                        "three_point_percentage": stat.three_point_percentage,
                        "free_throws_made": stat.free_throws_made,
                        "free_throws_attempted": stat.free_throws_attempted,
                        "free_throw_percentage": stat.free_throw_percentage,
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
                    }
                )

            df = pd.DataFrame(data)

            if filename is None:
                filename = f"player_stats_{self._get_timestamp_suffix()}"

            output_path = self.export_dir / "stats" / f"{filename}.parquet"

            table = pa.Table.from_pandas(df)
            pq.write_table(
                table, str(output_path), compression=self.settings.parquet_compression
            )

            logger.info(
                f"Exported {len(stats)} player stats to Parquet",
                path=str(output_path),
                size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
            )

            return str(output_path)

        except Exception as e:
            logger.error("Failed to export player stats to Parquet", error=str(e))
            return ""

    async def export_to_csv(
        self,
        df: pd.DataFrame,
        filename: str,
        category: str = "players",
    ) -> str:
        """
        Export DataFrame to CSV.

        Args:
            df: DataFrame to export
            filename: Output filename (without extension)
            category: Data category (players, teams, games, stats)

        Returns:
            Path to exported file
        """
        if df.empty:
            logger.warning("Empty DataFrame, nothing to export")
            return ""

        try:
            output_path = self.export_dir / category / f"{filename}.csv"
            df.to_csv(str(output_path), index=False)

            logger.info(
                f"Exported {len(df)} rows to CSV",
                path=str(output_path),
                size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
            )

            return str(output_path)

        except Exception as e:
            logger.error("Failed to export to CSV", error=str(e))
            return ""

    async def export_to_json(
        self,
        data: list[dict],
        filename: str,
        category: str = "players",
        pretty: bool = True,
    ) -> str:
        """
        Export data to JSON.

        Args:
            data: List of dictionaries to export
            filename: Output filename (without extension)
            category: Data category
            pretty: Whether to format JSON with indentation

        Returns:
            Path to exported file
        """
        if not data:
            logger.warning("Empty data, nothing to export")
            return ""

        try:
            output_path = self.export_dir / category / f"{filename}.json"

            with open(output_path, "w") as f:
                if pretty:
                    json.dump(data, f, indent=2, default=str)
                else:
                    json.dump(data, f, default=str)

            logger.info(
                f"Exported {len(data)} records to JSON",
                path=str(output_path),
                size_mb=round(output_path.stat().st_size / 1024 / 1024, 2),
            )

            return str(output_path)

        except Exception as e:
            logger.error("Failed to export to JSON", error=str(e))
            return ""

    def read_parquet(self, filepath: str) -> Optional[pd.DataFrame]:
        """
        Read Parquet file into DataFrame.

        Args:
            filepath: Path to Parquet file

        Returns:
            DataFrame or None if read fails
        """
        try:
            df = pd.read_parquet(filepath)
            logger.info(f"Read {len(df)} rows from Parquet", path=filepath)
            return df

        except Exception as e:
            logger.error("Failed to read Parquet file", path=filepath, error=str(e))
            return None

    def get_export_info(self, category: Optional[str] = None) -> dict[str, Any]:
        """
        Get information about exported files.

        Args:
            category: Optional category filter (players, teams, games, stats)

        Returns:
            Dictionary with file information
        """
        try:
            info = {}

            categories = [category] if category else ["players", "teams", "games", "stats"]

            for cat in categories:
                cat_dir = self.export_dir / cat
                if not cat_dir.exists():
                    continue

                files = []
                for file in cat_dir.glob("*.parquet"):
                    files.append(
                        {
                            "filename": file.name,
                            "size_mb": round(file.stat().st_size / 1024 / 1024, 2),
                            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                        }
                    )

                info[cat] = {
                    "file_count": len(files),
                    "files": sorted(files, key=lambda x: x["modified"], reverse=True),
                }

            return info

        except Exception as e:
            logger.error("Failed to get export info", error=str(e))
            return {}


# Global Parquet exporter instance
_parquet_exporter_instance: Optional[ParquetExporter] = None


def get_parquet_exporter() -> ParquetExporter:
    """
    Get global Parquet exporter instance.

    Returns:
        ParquetExporter instance
    """
    global _parquet_exporter_instance
    if _parquet_exporter_instance is None:
        _parquet_exporter_instance = ParquetExporter()
    return _parquet_exporter_instance
