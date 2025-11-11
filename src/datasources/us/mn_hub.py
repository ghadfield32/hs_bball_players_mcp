"""
Minnesota Basketball Hub DataSource Adapter

Scrapes player and team statistics from Minnesota Basketball Hub.
One of the best free high school basketball stats hubs in the U.S.
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
from ...utils import (
    clean_player_name,
    extract_table_data,
    get_text_or_none,
    parse_float,
    parse_height_to_inches,
    parse_html,
    parse_int,
)
from ..base import BaseDataSource


class MNHubDataSource(BaseDataSource):
    """
    Minnesota Basketball Hub data source adapter.

    Provides access to Minnesota high school basketball statistics.
    Public stats at https://stats.mnbasketballhub.com
    """

    source_type = DataSourceType.MN_HUB
    source_name = "Minnesota Basketball Hub"
    base_url = "https://stats.mnbasketballhub.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize MN Hub datasource."""
        super().__init__()

        # MN Hub-specific endpoints
        self.stats_url = f"{self.base_url}/stats"
        self.players_url = f"{self.base_url}/players"
        self.teams_url = f"{self.base_url}/teams"
        self.schedule_url = f"{self.base_url}/schedule"
        self.leaders_url = f"{self.base_url}/leaders"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Args:
            player_id: Player identifier

        Returns:
            Player object or None
        """
        try:
            # Construct player profile URL
            profile_url = f"{self.players_url}/{player_id}"

            html = await self.http_client.get_text(profile_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find player info section
            player_info = soup.find("div", class_=lambda x: x and "player-info" in str(x).lower())
            if not player_info:
                return None

            return self._parse_player_from_profile(soup, player_id, profile_url)

        except Exception as e:
            self.logger.error(f"Failed to get player", player_id=player_id, error=str(e))
            return None

    def _parse_player_from_profile(self, soup, player_id: str, url: str) -> Optional[Player]:
        """Parse player from profile page."""
        try:
            # Extract player name
            name_elem = soup.find(["h1", "h2"], class_=lambda x: x and "player-name" in str(x).lower())
            full_name = get_text_or_none(name_elem) if name_elem else ""

            if not full_name:
                return None

            # Split name
            name_parts = full_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else full_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Find info fields
            info_fields = soup.find_all(["div", "span"], class_=lambda x: x and "info" in str(x).lower())

            height = None
            position = None
            grad_year = None
            school = None
            team = None

            for field in info_fields:
                text = get_text_or_none(field)
                if not text:
                    continue

                # Parse different field types
                if "height" in text.lower() or "'" in text:
                    height = parse_height_to_inches(text)
                elif "position" in text.lower() or text.upper() in ["PG", "SG", "SF", "PF", "C"]:
                    try:
                        position = Position(text.upper().strip())
                    except ValueError:
                        pass
                elif "class" in text.lower() or "'" in text and len(text) == 2:
                    # Grad year like '25, '26
                    grad_year = parse_int("20" + text.replace("'", ""))
                elif "school" in text.lower():
                    school = text.replace("School:", "").strip()
                elif "team" in text.lower():
                    team = text.replace("Team:", "").strip()

            data_source = self.create_data_source_metadata(
                url=url, quality_flag=DataQualityFlag.COMPLETE
            )

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": full_name,
                "height_inches": height,
                "position": position,
                "grad_year": grad_year,
                "school_name": school,
                "school_state": "MN",
                "school_country": "USA",
                "team_name": team,
                "level": PlayerLevel.HIGH_SCHOOL,
                "profile_url": url,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {full_name}")

        except Exception as e:
            self.logger.error("Failed to parse player profile", error=str(e))
            return None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter
            limit: Maximum results

        Returns:
            List of Player objects
        """
        try:
            # Get stats page which lists players
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find stats table
            stats_table = soup.find("table")
            if not stats_table:
                self.logger.warning("No stats table found")
                return []

            rows = extract_table_data(stats_table)
            players = []

            data_source = self.create_data_source_metadata(
                url=self.stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            for row in rows[:limit * 2]:  # Get more for filtering
                player = self._parse_player_from_stats_row(row, data_source)
                if not player:
                    continue

                # Apply filters
                if name and name.lower() not in player.full_name.lower():
                    continue
                if team and (not player.team_name or team.lower() not in player.team_name.lower()):
                    continue

                players.append(player)

                if len(players) >= limit:
                    break

            self.logger.info(f"Found {len(players)} players")
            return players

        except Exception as e:
            self.logger.error("Failed to search players", error=str(e))
            return []

    def _parse_player_from_stats_row(self, row: dict, data_source) -> Optional[Player]:
        """Parse player from stats table row."""
        try:
            # Common column names
            player_name = (
                row.get("Player")
                or row.get("NAME")
                or row.get("Name")
                or row.get("PLAYER")
            )
            school = row.get("School") or row.get("SCHOOL") or row.get("Team")
            class_year = row.get("Class") or row.get("YR") or row.get("Year")
            position = row.get("Pos") or row.get("POS")

            if not player_name:
                return None

            # Clean and split name
            player_name = clean_player_name(player_name)
            name_parts = player_name.split()
            first_name = name_parts[0] if len(name_parts) > 0 else player_name
            last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

            # Parse position
            pos_enum = None
            if position:
                try:
                    pos_enum = Position(position.upper().strip())
                except ValueError:
                    pass

            # Parse grad year from class
            grad_year = None
            if class_year:
                # Could be '25, 2025, Sr, etc.
                year_num = parse_int(class_year.replace("'", ""))
                if year_num and year_num < 100:
                    grad_year = 2000 + year_num
                elif year_num and year_num > 2020:
                    grad_year = year_num

            # Create player ID
            player_id = f"mnhub_{player_name.lower().replace(' ', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "grad_year": grad_year,
                "school_name": school,
                "school_state": "MN",
                "school_country": "USA",
                "level": PlayerLevel.HIGH_SCHOOL,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e))
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        Args:
            player_id: Player identifier
            season: Season (uses current if None)

        Returns:
            PlayerSeasonStats or None
        """
        try:
            # Get from stats page
            html = await self.http_client.get_text(self.stats_url, cache_ttl=3600)
            soup = parse_html(html)

            stats_table = soup.find("table")
            if not stats_table:
                return None

            rows = extract_table_data(stats_table)

            # Find player row
            player_name = player_id.replace("mnhub_", "").replace("_", " ").title()

            for row in rows:
                row_player = row.get("Player") or row.get("NAME")
                if row_player and player_name.lower() in clean_player_name(row_player).lower():
                    return self._parse_season_stats_from_row(row, player_id, season or "2024-25")

            return None

        except Exception as e:
            self.logger.error("Failed to get player season stats", error=str(e))
            return None

    def _parse_season_stats_from_row(
        self, row: dict, player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """Parse season stats from table row."""
        try:
            player_name = clean_player_name(row.get("Player") or row.get("NAME") or "")
            school = row.get("School") or row.get("SCHOOL") or ""

            # Parse stats
            games = parse_int(row.get("GP") or row.get("G") or row.get("Games"))
            ppg = parse_float(row.get("PPG") or row.get("Points"))
            rpg = parse_float(row.get("RPG") or row.get("Rebounds"))
            apg = parse_float(row.get("APG") or row.get("Assists"))
            spg = parse_float(row.get("SPG") or row.get("Steals"))
            bpg = parse_float(row.get("BPG") or row.get("Blocks"))
            fgp = parse_float(row.get("FG%") or row.get("FG Pct"))
            tpp = parse_float(row.get("3P%") or row.get("3PT%"))
            ftp = parse_float(row.get("FT%") or row.get("FT Pct"))

            # Calculate totals from averages
            total_points = int(ppg * games) if ppg and games else None
            total_rebounds = int(rpg * games) if rpg and games else None
            total_assists = int(apg * games) if apg and games else None
            total_steals = int(spg * games) if spg and games else None
            total_blocks = int(bpg * games) if bpg and games else None

            stats_data = {
                "player_id": player_id,
                "player_name": player_name,
                "team_id": f"mnhub_{school.lower().replace(' ', '_')}",
                "season": season,
                "league": "Minnesota High School",
                "games_played": games or 0,
                "points": total_points,
                "points_per_game": ppg,
                "total_rebounds": total_rebounds,
                "rebounds_per_game": rpg,
                "assists": total_assists,
                "assists_per_game": apg,
                "steals": total_steals,
                "steals_per_game": spg,
                "blocks": total_blocks,
                "blocks_per_game": bpg,
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

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            PlayerGameStats or None
        """
        self.logger.warning("Individual game stats require game log access - not yet implemented")
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
            # Teams page should list all teams
            html = await self.http_client.get_text(self.teams_url, cache_ttl=7200)
            soup = parse_html(html)

            # Find teams table or list
            teams_table = soup.find("table")
            if not teams_table:
                return None

            rows = extract_table_data(teams_table)

            team_name = team_id.replace("mnhub_", "").replace("_", " ").title()

            for row in rows:
                row_team = row.get("Team") or row.get("School") or row.get("NAME")
                if row_team and team_name.lower() in row_team.lower():
                    return self._parse_team_from_row(row, team_id)

            return None

        except Exception as e:
            self.logger.error("Failed to get team", error=str(e))
            return None

    def _parse_team_from_row(self, row: dict, team_id: str) -> Optional[Team]:
        """Parse team from table row."""
        try:
            team_name = row.get("Team") or row.get("School") or row.get("NAME") or ""
            wins = parse_int(row.get("W") or row.get("Wins"))
            losses = parse_int(row.get("L") or row.get("Losses"))
            conference = row.get("Conference") or row.get("Conf")
            section = row.get("Section")

            data_source = self.create_data_source_metadata(
                url=self.teams_url, quality_flag=DataQualityFlag.COMPLETE
            )

            team_data = {
                "team_id": team_id,
                "team_name": team_name,
                "school_name": team_name,
                "state": "MN",
                "country": "USA",
                "level": TeamLevel.HIGH_SCHOOL_VARSITY,
                "league": "Minnesota High School",
                "conference": conference or section,
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
        Get games from schedule.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of Game objects
        """
        self.logger.warning("Game schedule parsing not yet implemented for MN Hub")
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
            # MN Hub has dedicated leaders page
            html = await self.http_client.get_text(self.leaders_url, cache_ttl=3600)
            soup = parse_html(html)

            # Find the specific stat table
            # Could have separate tables for PPG, RPG, APG, etc.
            tables = soup.find_all("table")

            for table in tables:
                # Check if this is the right stat table
                header = table.find_previous(["h2", "h3"])
                if header and stat.lower() in get_text_or_none(header, strip=True).lower():
                    rows = extract_table_data(table)
                    leaderboard = []

                    for i, row in enumerate(rows[:limit], 1):
                        player_name = row.get("Player") or row.get("NAME")
                        school = row.get("School") or row.get("Team")
                        stat_value = parse_float(
                            row.get(stat.upper())
                            or row.get("Value")
                            or row.get("AVG")
                            or row.get("Total")
                        )

                        if player_name and stat_value is not None:
                            leaderboard.append(
                                {
                                    "rank": i,
                                    "player_id": f"mnhub_{clean_player_name(player_name).lower().replace(' ', '_')}",
                                    "player_name": clean_player_name(player_name),
                                    "team_name": school,
                                    "stat_value": stat_value,
                                    "stat_name": stat,
                                    "season": season or "2024-25",
                                }
                            )

                    if leaderboard:
                        return leaderboard

            # If no specific table found, use main stats page
            return await self._get_leaderboard_from_stats(stat, season, limit)

        except Exception as e:
            self.logger.error("Failed to get leaderboard", error=str(e))
            return []

    async def _get_leaderboard_from_stats(
        self, stat: str, season: Optional[str], limit: int
    ) -> list[dict]:
        """Get leaderboard by sorting main stats page."""
        # Would need to fetch all players and sort by stat
        # For now, return empty
        return []
