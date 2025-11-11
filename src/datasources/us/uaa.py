"""
UAA (Under Armour Association) DataSource Adapter

Scrapes player and team statistics from Under Armour Association circuit.
National grassroots circuit with multiple event stops and comprehensive team data.

URL: https://underarmourassociation.com
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

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
    parse_html,
    parse_int,
    parse_record,
)
from ...utils.scraping_helpers import (
    build_leaderboard_entry,
    extract_links_from_table,
    find_stat_table,
    parse_grad_year,
    parse_player_from_row,
    parse_season_stats_from_row,
    standardize_stat_columns,
)
from ..base import BaseDataSource


class UAADataSource(BaseDataSource):
    """
    UAA (Under Armour Association) data source adapter.

    Provides access to Under Armour national grassroots circuit statistics.
    Official UA circuit with comprehensive event-based coverage.

    Base URL: https://underarmourassociation.com

    Circuit Structure:
    - Multiple event stops throughout the season (April-July)
    - Division-based competition (15U, 16U, 17U)
    - Team rosters and schedules
    - Event-specific stats and standings
    """

    source_type = DataSourceType.UAA
    source_name = "Under Armour Association"
    base_url = "https://underarmourassociation.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize UAA datasource."""
        super().__init__()

        # Circuit-level endpoints
        self.stats_url = f"{self.base_url}/stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"
        self.teams_url = f"{self.base_url}/teams"
        self.events_url = f"{self.base_url}/events"

        self.logger.info("UAA datasource initialized", base_url=self.base_url)

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None, season: Optional[str] = None) -> str:
        """
        Build UAA player ID with namespace prefix.

        Args:
            player_name: Player's full name
            team_name: Optional team name for uniqueness
            season: Optional season for uniqueness

        Returns:
            Formatted player ID: "uaa:{name}" or "uaa:{name}:{team}:{season}"

        Example:
            "john_doe" -> "uaa:john_doe"
            "john_doe", "Team Elite", "2024" -> "uaa:john_doe:team_elite:2024"
        """
        name_part = clean_player_name(player_name).lower().replace(" ", "_")

        parts = [f"uaa:{name_part}"]

        if team_name:
            team_part = clean_player_name(team_name).lower().replace(" ", "_")
            parts.append(team_part)

        if season:
            parts.append(season)

        return ":".join(parts)

    def _build_team_id(self, team_name: str, division: Optional[str] = None) -> str:
        """
        Build UAA team ID.

        Args:
            team_name: Team name
            division: Optional division (15U, 16U, 17U)

        Returns:
            Formatted team ID: "uaa:team_{name}" or "uaa:team_{name}_{division}"
        """
        team_part = clean_player_name(team_name).lower().replace(" ", "_")

        if division:
            return f"uaa:team_{team_part}_{division.lower()}"

        return f"uaa:team_{team_part}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from UAA.

        Args:
            player_id: UAA player identifier (format: uaa:{name}:...)

        Returns:
            Player object or None
        """
        # Extract name from player_id
        if player_id.startswith("uaa:"):
            parts = player_id.split(":")
            name = parts[1].replace("_", " ") if len(parts) > 1 else player_id.replace("uaa:", "").replace("_", " ")
        else:
            name = player_id.replace("_", " ")

        # Search for player in current season stats
        players = await self.search_players(name=name, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        division: Optional[str] = None,  # 15U, 16U, 17U
        grad_year: Optional[int] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in UAA stats tables.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter (e.g., "2024")
            division: Division filter (15U, 16U, 17U)
            grad_year: Graduation year filter
            limit: Maximum results

        Returns:
            List of Player objects
        """
        self.logger.info(
            "Searching UAA players",
            name=name,
            team=team,
            season=season,
            division=division,
            grad_year=grad_year,
        )

        try:
            # Build stats URL with filters
            current_year = datetime.now().year
            season = season or str(current_year)

            stats_url = f"{self.stats_url}/{season}"
            if division:
                stats_url = f"{stats_url}/{division}"

            # Fetch stats page
            html = await self.http_client.get_text(stats_url, cache_ttl=3600)
            soup = parse_html(html)

            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find player stats table
            table = find_stat_table(soup, table_class_hint="stats")

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit * 2]:  # Get extra for filtering
                    player = self._parse_player_from_stats_row(row, season, division, data_source)

                    if not player:
                        continue

                    # Apply filters
                    if name and name.lower() not in player.full_name.lower():
                        continue
                    if team and team.lower() not in (player.team_name or "").lower():
                        continue
                    if grad_year and player.grad_year != grad_year:
                        continue

                    players.append(player)

                    if len(players) >= limit:
                        break

            self.logger.info(f"Found {len(players)} UAA players")
            return players

        except Exception as e:
            self.logger.error("Failed to search UAA players", error=str(e))
            return []

    def _parse_player_from_stats_row(
        self, row: Dict[str, Any], season: str, division: Optional[str], data_source
    ) -> Optional[Player]:
        """
        Parse player from stats table row.

        Args:
            row: Row dictionary from stats table
            season: Season identifier
            division: Division identifier
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Extract common columns
            player_name = (
                row.get("Player")
                or row.get("NAME")
                or row.get("Name")
                or row.get("PLAYER NAME")
            )

            team_name = (
                row.get("Team")
                or row.get("TEAM")
                or row.get("School")
                or row.get("Club")
            )

            position_str = row.get("Pos") or row.get("POS") or row.get("Position")
            height_str = row.get("Ht") or row.get("Height") or row.get("HT")
            class_str = row.get("Class") or row.get("Yr") or row.get("Year")
            number_str = row.get("#") or row.get("No") or row.get("Jersey")

            if not player_name:
                return None

            # Parse name
            name_parts = player_name.strip().split()
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])
            else:
                first_name = player_name
                last_name = ""

            # Parse position
            pos_enum = None
            if position_str:
                try:
                    pos_enum = Position(position_str.upper().strip())
                except ValueError:
                    pass

            # Parse height (format: 6-3 or 6'3")
            height_inches = None
            if height_str:
                if "-" in height_str or "'" in height_str:
                    try:
                        parts = height_str.replace("'", "-").replace('"', "").split("-")
                        if len(parts) == 2:
                            feet = int(parts[0])
                            inches = int(parts[1])
                            height_inches = feet * 12 + inches
                    except:
                        pass
                else:
                    height_inches = parse_int(height_str)

            # Parse grad year
            grad_year = parse_grad_year(class_str)

            # Build player ID
            player_id = self._build_player_id(player_name, team_name, season)

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "height_inches": height_inches,
                "jersey_number": parse_int(number_str),
                "team_name": team_name,
                "school_country": "USA",
                "level": PlayerLevel.HIGH_SCHOOL,
                "season": season,
                "grad_year": grad_year,
                "data_source": data_source,
            }

            # Parse season stats if available
            stats = parse_season_stats_from_row(row, player_id, season)
            if stats:
                player_data["season_stats"] = stats

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from row", error=str(e), row=row)
            return None

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season statistics.

        Args:
            player_id: Player identifier
            season: Season filter

        Returns:
            PlayerSeasonStats or None
        """
        # Extract name from player_id
        if player_id.startswith("uaa:"):
            parts = player_id.split(":")
            name = parts[1].replace("_", " ") if len(parts) > 1 else ""
            if not season and len(parts) > 3:
                season = parts[3]
        else:
            name = player_id.replace("_", " ")

        current_year = datetime.now().year
        season = season or str(current_year)

        # Search for player to get their stats
        players = await self.search_players(name=name, season=season, limit=1)

        if players and players[0].season_stats:
            return players[0].season_stats

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
            # Extract team name from ID
            if team_id.startswith("uaa:team_"):
                team_name = team_id.replace("uaa:team_", "").replace("_", " ").split()[0]
            else:
                team_name = team_id.replace("_", " ")

            teams_url = f"{self.teams_url}"
            html = await self.http_client.get_text(teams_url, cache_ttl=7200)
            soup = parse_html(html)

            # Find teams table
            table = soup.find("table", class_=lambda x: x and "team" in str(x).lower())

            if table:
                rows = extract_table_data(table)

                for row in rows:
                    row_team = row.get("Team") or row.get("TEAM") or row.get("Name")

                    if row_team and team_name.lower() in row_team.lower():
                        # Extract record
                        record_str = row.get("Record") or row.get("W-L")
                        wins, losses = None, None
                        if record_str:
                            wins, losses = parse_record(record_str)

                        team_data = {
                            "team_id": team_id,
                            "name": row_team,
                            "school": row_team,
                            "level": TeamLevel.CLUB,
                            "season": str(datetime.now().year),
                            "wins": wins,
                            "losses": losses,
                            "data_source": self.create_data_source_metadata(
                                url=teams_url, quality_flag=DataQualityFlag.COMPLETE
                            ),
                        }

                        return self.validate_and_log_data(Team, team_data, f"team {row_team}")

            return None

        except Exception as e:
            self.logger.error("Failed to get team", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        event: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from UAA.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            event: Event/stop filter
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            current_year = datetime.now().year
            season = season or str(current_year)

            schedule_url = f"{self.schedule_url}/{season}"
            if event:
                schedule_url = f"{schedule_url}/{event}"

            html = await self.http_client.get_text(schedule_url, cache_ttl=1800)
            soup = parse_html(html)

            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.PARTIAL
            )

            # Find schedule table
            table = soup.find("table", class_=lambda x: x and ("schedule" in str(x).lower() or "game" in str(x).lower()))

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    game = self._parse_game_from_row(row, season, data_source)
                    if game:
                        # Apply filters
                        if team_id and team_id not in [game.home_team_id, game.away_team_id]:
                            continue
                        if start_date and game.game_date and game.game_date < start_date:
                            continue
                        if end_date and game.game_date and game.game_date > end_date:
                            continue

                        games.append(game)

            self.logger.info(f"Found {len(games)} games")
            return games

        except Exception as e:
            self.logger.error("Failed to get games", error=str(e))
            return []

    def _parse_game_from_row(
        self, row: Dict[str, Any], season: str, data_source
    ) -> Optional[Game]:
        """Parse game from schedule row."""
        try:
            home_team = row.get("Home") or row.get("Home Team")
            away_team = row.get("Away") or row.get("Away Team") or row.get("Visitor")
            score = row.get("Score") or row.get("Result")
            date_str = row.get("Date")
            time_str = row.get("Time")

            if not home_team or not away_team:
                return None

            # Parse score
            home_score, away_score = None, None
            status = GameStatus.SCHEDULED

            if score and "-" in score:
                parts = score.split("-")
                if len(parts) == 2:
                    home_score = parse_int(parts[0].strip())
                    away_score = parse_int(parts[1].strip())
                    if home_score is not None and away_score is not None:
                        status = GameStatus.COMPLETED

            # Parse date
            game_date = None
            if date_str:
                try:
                    # Try MM/DD/YYYY format
                    if "/" in date_str:
                        month, day, year = date_str.split("/")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                except Exception:
                    pass

            game_id = f"uaa:{home_team.lower().replace(' ', '_')}:{away_team.lower().replace(' ', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_team_id": self._build_team_id(home_team),
                "away_team_id": self._build_team_id(away_team),
                "game_date": game_date,
                "game_type": GameType.REGULAR_SEASON,
                "status": status,
                "home_score": home_score,
                "away_score": away_score,
                "season": season,
                "data_source": data_source,
            }

            return self.validate_and_log_data(Game, game_data, f"game {game_id}")

        except Exception as e:
            self.logger.error("Failed to parse game", error=str(e))
            return None

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category (points, rebounds, assists, etc.)
            season: Season filter
            division: Division filter (15U, 16U, 17U)
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            current_year = datetime.now().year
            season = season or str(current_year)

            # Search players to get stats
            players = await self.search_players(season=season, division=division, limit=limit * 2)

            # Build leaderboard
            leaderboard = []

            for player in players:
                if not player.season_stats:
                    continue

                stat_value = None
                if stat.lower() in ["points", "ppg", "pts"]:
                    stat_value = player.season_stats.points_per_game
                elif stat.lower() in ["rebounds", "rpg", "reb"]:
                    stat_value = player.season_stats.rebounds_per_game
                elif stat.lower() in ["assists", "apg", "ast"]:
                    stat_value = player.season_stats.assists_per_game
                elif stat.lower() in ["steals", "spg", "stl"]:
                    stat_value = player.season_stats.steals_per_game
                elif stat.lower() in ["blocks", "bpg", "blk"]:
                    stat_value = player.season_stats.blocks_per_game

                if stat_value is not None:
                    leaderboard.append(
                        build_leaderboard_entry(
                            player=player,
                            stat_name=stat,
                            stat_value=stat_value,
                            season=season,
                        )
                    )

            # Sort and limit
            leaderboard.sort(key=lambda x: x["stat_value"], reverse=True)
            return leaderboard[:limit]

        except Exception as e:
            self.logger.error("Failed to get leaderboard", error=str(e))
            return []
