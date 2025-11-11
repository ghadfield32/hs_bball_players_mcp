"""
PSAL (NYC Public Schools Athletic League) DataSource Adapter

Scrapes player and team statistics from PSAL (New York City).
Good coverage for NYC high school basketball.
"""

from datetime import datetime
from typing import Optional

from ...models import (
    DataQualityFlag,
    DataSourceRegion,
    DataSourceType,
    Game,
    GameStatus,
    Player,
    PlayerGameStats,
    PlayerLevel,
    PlayerSeasonStats,
    Position,
    Team,
    TeamLevel,
)
from ...utils import (
    clean_player_name,
    extract_table_data,
    get_text_or_none,
    parse_float,
    parse_html,
    parse_int,
    parse_record,
)
from ..base import BaseDataSource


class PSALDataSource(BaseDataSource):
    """
    PSAL (NYC Public Schools Athletic League) data source adapter.

    Provides access to NYC high school basketball statistics.
    Public stats at https://www.psal.org
    """

    source_type = DataSourceType.PSAL
    source_name = "NYC PSAL"
    base_url = "https://www.psal.org"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize PSAL datasource."""
        super().__init__()

        # PSAL-specific endpoints
        # Sport code 001 = Basketball
        self.basketball_url = f"{self.base_url}/sports/sport.aspx?spCode=001"
        self.standings_url = f"{self.base_url}/sports/standings.aspx?spCode=001"
        self.leaders_url = f"{self.base_url}/sports/top-player.aspx?spCode=001"
        self.teams_url = f"{self.base_url}/sports/team.aspx?spCode=001"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        PSAL doesn't have individual player profile pages.
        Search through leaderboards instead.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
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
        Search for players in PSAL leaderboards.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Get statistical leaders page
            html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # PSAL has multiple stat tables (PPG, RPG, APG, etc.)
            tables = soup.find_all("table")

            players = []
            seen_players = set()

            data_source = self.create_data_source_metadata(
                url=self.leaders_url, quality_flag=DataQualityFlag.PARTIAL
            )

            for table in tables:
                rows = extract_table_data(table)

                for row in rows:
                    player = self._parse_player_from_leaders_row(row, data_source)
                    if not player:
                        continue

                    # Avoid duplicates
                    if player.player_id in seen_players:
                        continue

                    # Apply filters
                    if name and name.lower() not in player.full_name.lower():
                        continue
                    if team and (
                        not player.school_name or team.lower() not in player.school_name.lower()
                    ):
                        continue

                    players.append(player)
                    seen_players.add(player.player_id)

                    if len(players) >= limit:
                        break

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} players")
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e))
            return []

    def _parse_player_from_leaders_row(self, row: dict, data_source) -> Optional[Player]:
        """Parse player from leaderboard row."""
        try:
            # PSAL column names
            player_name = row.get("Player") or row.get("Name") or row.get("PLAYER NAME")
            school = row.get("School") or row.get("SCHOOL") or row.get("Team")
            grade = row.get("Grade") or row.get("YR")

            if not player_name:
                return None

            # Clean name
            player_name = clean_player_name(player_name)
            name_parts = player_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else player_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Parse grad year from grade
            grad_year = None
            if grade:
                grade_map = {"Fr": 2028, "So": 2027, "Jr": 2026, "Sr": 2025}
                grad_year = grade_map.get(grade.strip())

            # Create player ID
            player_id = f"psal_{player_name.lower().replace(' ', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "school_name": school,
                "school_city": "New York",
                "school_state": "NY",
                "school_country": "USA",
                "grad_year": grad_year,
                "level": PlayerLevel.HIGH_SCHOOL,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from leaders row", error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        PSAL primarily shows season averages in leaderboards.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Get leaders page
            html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            player_name = player_id.replace("psal_", "").replace("_", " ").title()

            # Search through stat tables
            tables = soup.find_all("table")

            # Collect stats from different tables
            stats_dict = {}

            for table in tables:
                # Check table header for stat type
                header = table.find_previous(["h2", "h3", "h4"])
                stat_type = get_text_or_none(header).lower() if header else ""

                rows = extract_table_data(table)

                for row in rows:
                    row_player = clean_player_name(row.get("Player") or row.get("Name") or "")
                    if player_name.lower() in row_player.lower():
                        # Found the player in this table
                        # Merge stats
                        for key, value in row.items():
                            if key not in ["Player", "Name", "School", "Team", "Grade"]:
                                stats_dict[key] = value

            if not stats_dict:
                return None

            # Parse collected stats
            return self._parse_season_stats_from_dict(stats_dict, player_id, season or "2024-25")

        except Exception as e:
            self.logger.error("Failed to get player season stats", error=str(e))
            return None

    def _parse_season_stats_from_dict(
        self, stats: dict, player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """Parse season stats from collected stats dictionary."""
        try:
            games = parse_int(stats.get("GP") or stats.get("G") or stats.get("Games"))
            ppg = parse_float(stats.get("PPG") or stats.get("Points"))
            rpg = parse_float(stats.get("RPG") or stats.get("Rebounds"))
            apg = parse_float(stats.get("APG") or stats.get("Assists"))
            spg = parse_float(stats.get("SPG") or stats.get("Steals"))
            bpg = parse_float(stats.get("BPG") or stats.get("Blocks"))

            # Calculate totals
            total_points = int(ppg * games) if ppg and games else None
            total_rebounds = int(rpg * games) if rpg and games else None
            total_assists = int(apg * games) if apg and games else None

            stats_data = {
                "player_id": player_id,
                "player_name": player_id.replace("psal_", "").replace("_", " ").title(),
                "team_id": "psal_unknown",
                "season": season,
                "league": "PSAL",
                "games_played": games or 0,
                "points": total_points,
                "points_per_game": ppg,
                "total_rebounds": total_rebounds,
                "rebounds_per_game": rpg,
                "assists": total_assists,
                "assists_per_game": apg,
                "steals_per_game": spg,
                "blocks_per_game": bpg,
            }

            return self.validate_and_log_data(PlayerSeasonStats, stats_data, "season stats")

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
            return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game statistics.

        PSAL doesn't provide individual game stats publicly.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning("Individual game stats not available in PSAL public pages")
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        try:
            # Get standings page
            html = await self.http_client.get_text(self.standings_url, cache_ttl=7200)
            soup = parse_html(html)

            # PSAL has multiple divisions
            tables = soup.find_all("table")

            team_name = team_id.replace("psal_", "").replace("_", " ").title()

            for table in tables:
                rows = extract_table_data(table)

                for row in rows:
                    row_team = row.get("Team") or row.get("School") or row.get("SCHOOL")
                    if row_team and team_name.lower() in row_team.lower():
                        return self._parse_team_from_standings_row(row, team_id, table)

            return None

        except Exception as e:
            self.logger.error("Failed to get team", error=str(e))
            return None

    def _parse_team_from_standings_row(
        self, row: dict, team_id: str, table
    ) -> Optional[Team]:
        """Parse team from standings row."""
        try:
            team_name = row.get("Team") or row.get("School") or row.get("SCHOOL") or ""

            # Parse record
            record = row.get("Record") or row.get("W-L")
            wins, losses = parse_record(record) if record else (None, None)

            # Try separate W/L columns
            if wins is None:
                wins = parse_int(row.get("W") or row.get("Wins"))
            if losses is None:
                losses = parse_int(row.get("L") or row.get("Losses"))

            # Get division from table header
            division = None
            header = table.find_previous(["h2", "h3"])
            if header:
                division = get_text_or_none(header)

            data_source = self.create_data_source_metadata(
                url=self.standings_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "city": "New York",
                "state": "NY",
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": "PSAL",
                "conference": division,
                "season": "2024-25",
                "wins": wins,
                "losses": losses,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Team, team_data, f"team {team_name}")

        except Exception as e:
            self.logger.error("Failed to parse team", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from PSAL.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        self.logger.warning("Game schedule parsing not yet implemented for PSAL")
        return []

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category
            season: Season filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find table for specific stat
            tables = soup.find_all("table")

            for table in tables:
                # Check if this is the right stat
                header = table.find_previous(["h2", "h3", "h4"])
                if header and stat.lower() in get_text_or_none(header).lower():
                    rows = extract_table_data(table)
                    leaderboard = []

                    for i, row in enumerate(rows[:limit], 1):
                        player_name = clean_player_name(
                            row.get("Player") or row.get("Name") or ""
                        )
                        school = row.get("School") or row.get("SCHOOL")
                        stat_value = parse_float(
                            row.get(stat.upper())
                            or row.get("Value")
                            or row.get("AVG")
                            or row.get("PPG")
                            or row.get("RPG")
                            or row.get("APG")
                        )

                        if player_name and stat_value is not None:
                            leaderboard.append(
                                {
                                    "rank": i,
                                    "player_id": f"psal_{player_name.lower().replace(' ', '_')}",
                                    "player_name": player_name,
                                    "team_name": school,
                                    "stat_value": stat_value,
                                    "stat_name": stat,
                                    "season": season or "2024-25",
                                }
                            )

                    if leaderboard:
                        return leaderboard

            return []

        except Exception as e:
            self.logger.error("Failed to get leaderboard", error=str(e))
            return []
