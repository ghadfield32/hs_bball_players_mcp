"""
EYBL (Nike Elite Youth Basketball League) DataSource Adapter

Scrapes player and game statistics from Nike EYBL public pages.
"""

from datetime import datetime
from typing import Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    GameType,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Position,
    Team,
    TeamLevel,
)
from ...utils import extract_table_data, get_text_or_none, parse_float, parse_html, parse_int
from ..base import BaseDataSource


class EYBLDataSource(BaseDataSource):
    """
    Nike EYBL data source adapter.

    Provides access to Nike EYBL stats, schedules, standings, and leaderboards.
    Public stats pages at https://nikeeyb.com
    """

    source_type = DataSourceType.EYBL
    source_name = "Nike EYBL"
    base_url = "https://nikeeyb.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize EYBL datasource."""
        super().__init__()

        # EYBL-specific endpoints
        self.stats_url = f"{self.base_url}/cumulative-season-stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Note: EYBL doesn't have direct player profile pages accessible by ID.
        Need to search through stats tables.

        Args:
            player_id: Player identifier (EYBL uses player name as ID)

        Returns:
            Player object or None
        """
        # Search for player in current season stats
        players = await self.search_players(name=player_id, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in EYBL stats tables.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season (currently uses latest)
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Fetch cumulative stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            stats_table = soup.find("table", class_=lambda x: x and "stats" in x.lower())
            if not stats_table:
                # Try finding any table
                stats_table = soup.find("table")

            if not stats_table:
                self.logger.warning("No stats table found on EYBL stats page")
                return []

            # Extract table data
            rows = extract_table_data(stats_table)

            players = []
            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            for row in rows[:limit]:
                # Parse player from row
                player = self._parse_player_from_stats_row(row, data_source)
                if player:
                    # Filter by name if provided
                    if name and name.lower() not in player.full_name.lower():
                        continue

                    # Filter by team if provided
                    if team and (
                        not player.team_name or team.lower() not in player.team_name.lower()
                    ):
                        continue

                    players.append(player)

            self.logger.info(f"Found {len(players)} players", filters={"name": name, "team": team})
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e))
            return []

    def _parse_player_from_stats_row(self, row: dict, data_source) -> Optional[Player]:
        """
        Parse player from stats table row.

        Args:
            row: Row dictionary from stats table
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Common column names (may vary)
            player_name = row.get("Player") or row.get("NAME") or row.get("Name")
            team_name = row.get("Team") or row.get("TEAM") or row.get("Club")
            position = row.get("Pos") or row.get("POS") or row.get("Position")

            if not player_name:
                return None

            # Split name into first/last
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""

            # Parse position
            pos_enum = None
            if position:
                try:
                    pos_enum = Position(position.upper().strip())
                except ValueError:
                    pass

            # Create player ID from name (sanitized)
            player_id = f"eybl_{player_name.lower().replace(' ', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "team_name": team_name,
                "level": PlayerLevel.GRASSROOTS,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e), row=row)
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics from cumulative stats page.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Fetch cumulative stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            stats_table = soup.find("table")
            if not stats_table:
                return None

            # Extract table data
            rows = extract_table_data(stats_table)

            # Find player row (match by name from player_id)
            player_name = player_id.replace("eybl_", "").replace("_", " ").title()

            for row in rows:
                row_player_name = row.get("Player") or row.get("NAME") or row.get("Name")
                if row_player_name and player_name.lower() in row_player_name.lower():
                    # Parse stats from row
                    return self._parse_season_stats_from_row(row, player_id, season or "2024-25")

            self.logger.warning(f"Player not found in stats", player_id=player_id)
            return None

        except Exception as e:
            self.logger.error("Failed to get player season stats", player_id=player_id, error=str(e))
            return None

    def _parse_season_stats_from_row(
        self, row: dict, player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """
        Parse season stats from table row.

        Args:
            row: Row dictionary
            player_id: Player ID
            season: Season string

        Returns:
            PlayerSeasonStats or None
        """
        try:
            player_name = row.get("Player") or row.get("NAME") or row.get("Name", "")
            team_name = row.get("Team") or row.get("TEAM") or ""

            # Parse stats (column names may vary)
            games_played = parse_int(row.get("GP") or row.get("G") or row.get("Games"))
            points = parse_int(row.get("PTS") or row.get("Points"))
            ppg = parse_float(row.get("PPG") or row.get("Points Per Game"))
            rebounds = parse_int(row.get("REB") or row.get("Rebounds"))
            rpg = parse_float(row.get("RPG") or row.get("Rebounds Per Game"))
            assists = parse_int(row.get("AST") or row.get("Assists"))
            apg = parse_float(row.get("APG") or row.get("Assists Per Game"))
            steals = parse_int(row.get("STL") or row.get("Steals"))
            blocks = parse_int(row.get("BLK") or row.get("Blocks"))
            fgm = parse_int(row.get("FGM") or row.get("FG Made"))
            fga = parse_int(row.get("FGA") or row.get("FG Attempted"))
            tpm = parse_int(row.get("3PM") or row.get("3P Made"))
            tpa = parse_int(row.get("3PA") or row.get("3P Attempted"))
            ftm = parse_int(row.get("FTM") or row.get("FT Made"))
            fta = parse_int(row.get("FTA") or row.get("FT Attempted"))

            stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "team_id": f"eybl_team_{team_name.lower().replace(' ', '_')}",
                "season": season,
                "league": "Nike EYBL",
                "games_played": games_played or 0,
                "points": points,
                "points_per_game": ppg,
                "total_rebounds": rebounds,
                "rebounds_per_game": rpg,
                "assists": assists,
                "assists_per_game": apg,
                "steals": steals,
                "steals_per_game": parse_float(row.get("SPG")),
                "blocks": blocks,
                "blocks_per_game": parse_float(row.get("BPG")),
                "field_goals_made": fgm,
                "field_goals_attempted": fga,
                "three_pointers_made": tpm,
                "three_pointers_attempted": tpa,
                "free_throws_made": ftm,
                "free_throws_attempted": fta,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_name}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        Note: EYBL cumulative stats page doesn't show individual game stats.
        Would need to access specific game box scores.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning("Individual game stats not yet implemented for EYBL")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        # EYBL teams can be extracted from standings page
        try:
            html = await self.http_client.get_text(self.standings_url, cache_ttl=7200)
            soup = parse_html(html)

            # Find standings table
            table = soup.find("table")
            if not table:
                return None

            rows = extract_table_data(table)

            # Find team row
            team_name = team_id.replace("eybl_team_", "").replace("_", " ").title()

            for row in rows:
                row_team = row.get("Team") or row.get("TEAM") or row.get("Name")
                if row_team and team_name.lower() in row_team.lower():
                    return self._parse_team_from_row(row, team_id)

            return None

        except Exception as e:
            self.logger.error("Failed to get team", team_id=team_id, error=str(e))
            return None

    def _parse_team_from_row(self, row: dict, team_id: str) -> Optional[Team]:
        """Parse team from standings row."""
        team_name = row.get("Team") or row.get("TEAM") or row.get("Name", "")
        wins = parse_int(row.get("W") or row.get("Wins"))
        losses = parse_int(row.get("L") or row.get("Losses"))

        data_source = self.create_data_source_metadata(
            url=self.standings_url, quality_flag=DataQualityFlag.COMPLETE
        )

        team_data = {
            "team_id": team_id,
            "team_name": team_name,
            "level": TeamLevel.GRASSROOTS,
            "league": "Nike EYBL",
            "season": "2024-25",
            "wins": wins,
            "losses": losses,
            "data_source": data_source,
        }

        return self.validate_and_log_data(Team, team_data, f"team {team_name}")

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from schedule page.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        self.logger.warning("Games/schedule parsing not yet implemented for EYBL")
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        EYBL cumulative stats page is essentially a leaderboard.

        Args:
            stat: Stat category
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            # Get all players
            players_with_stats = await self.search_players(limit=limit)

            # Note: Would need to sort by requested stat
            # For now, return first N players

            leaderboard = []
            for i, player in enumerate(players_with_stats[:limit], 1):
                leaderboard.append(
                    {
                        "rank": i,
                        "player_id": player.player_id,
                        "player_name": player.full_name,
                        "team_name": player.team_name,
                        "stat_name": stat,
                        "season": season or "2024-25",
                    }
                )

            return leaderboard

        except Exception as e:
            self.logger.error("Failed to get leaderboard", stat=stat, error=str(e))
            return []
