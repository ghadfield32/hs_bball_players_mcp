"""
NPA (National Preparatory Association) DataSource Adapter

Scrapes player and game statistics from Canada's national prep basketball league.
NPA is the premier Canadian prep circuit featuring top academies and high schools.

URL: https://www.npacanada.com
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
    build_leaderboard_entry,
    extract_table_data,
    get_text_or_none,
    parse_float,
    parse_html,
    parse_int,
    parse_record,
)
from ..base import BaseDataSource


class NPADataSource(BaseDataSource):
    """
    NPA (National Preparatory Association) data source adapter.

    Provides access to Canada's premier prep basketball league:
    - NPA Division 1 (Top tier prep)
    - NPA Division 2 (Second tier)
    - Features top Canadian prep academies

    Coverage:
    - Player statistics and rosters
    - Game schedules and results
    - Team standings
    - Statistical leaders
    - Showcase events

    Top NPA programs include CIA Bounce, Athlete Institute, UPlay Canada,
    Orangeville Prep, and other elite Canadian academies.
    """

    source_type = DataSourceType.NPA
    source_name = "NPA Canada"
    base_url = "https://www.npacanada.com"
    region = DataSourceRegion.CANADA

    # Division mapping
    DIVISIONS = {
        "d1": "division-1",
        "d2": "division-2",
        "div1": "division-1",
        "div2": "division-2",
    }

    def __init__(self):
        """Initialize NPA datasource."""
        super().__init__()

        # NPA-specific endpoints (subject to website structure)
        self.stats_url = f"{self.base_url}/stats"
        self.players_url = f"{self.base_url}/players"
        self.teams_url = f"{self.base_url}/teams"
        self.schedule_url = f"{self.base_url}/schedule"
        self.leaders_url = f"{self.base_url}/leaders"

        # Current season (Canadian season format: YYYY-YY)
        current_year = datetime.now().year
        # Canadian prep season starts in September
        if datetime.now().month >= 9:
            self.current_season = f"{current_year}-{str(current_year + 1)[-2:]}"
        else:
            self.current_season = f"{current_year - 1}-{str(current_year)[-2:]}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from NPA.

        Args:
            player_id: NPA player identifier (format: npa_firstname_lastname)

        Returns:
            Player object or None
        """
        # Extract name
        name = player_id.replace("npa_", "").replace("_", " ")
        players = await self.search_players(name=name, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        division: Optional[str] = None,  # "d1" or "d2"
        grad_year: Optional[int] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in NPA.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter (format: 2024-25)
            division: Division filter ("d1" or "d2")
            grad_year: Graduation year filter
            limit: Maximum results

        Returns:
            List of Player objects
        """
        self.logger.info(
            "Searching NPA players",
            name=name,
            team=team,
            season=season,
            division=division,
            grad_year=grad_year,
        )

        try:
            season = season or self.current_season
            division = division or "d1"  # Default to Division 1

            # Get division path
            division_path = self.DIVISIONS.get(division.lower(), "division-1")

            # Construct stats URL
            stats_url = f"{self.base_url}/{division_path}/{season}/stats"

            html = await self.http_client.get_text(stats_url, cache_ttl=7200)
            soup = parse_html(html)

            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find player stats table
            table = soup.find("table", class_=lambda x: x and ("stats" in str(x).lower() or "player" in str(x).lower()))

            if not table:
                # Try alternative selectors
                table = soup.find("table")

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    player = self._parse_player_from_stats_row(
                        row, season, division, data_source
                    )
                    if player:
                        # Apply filters
                        if name and name.lower() not in player.full_name.lower():
                            continue
                        if team and team.lower() not in (player.team_name or "").lower():
                            continue
                        if grad_year and player.grad_year != grad_year:
                            continue

                        players.append(player)

            self.logger.info(f"Found {len(players)} NPA players")
            return players

        except Exception as e:
            self.logger.error("Failed to search NPA players", error=str(e))
            return []

    def _parse_player_from_stats_row(
        self, row: Dict[str, Any], season: str, division: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from statistics table row.

        Args:
            row: Row dictionary from stats table
            season: Season identifier
            division: Division identifier
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Common column names
            player_name = (
                row.get("Player")
                or row.get("Name")
                or row.get("PLAYER")
                or row.get("NAME")
            )

            team_name = (
                row.get("Team")
                or row.get("School")
                or row.get("Academy")
                or row.get("TEAM")
            )

            position = row.get("Pos") or row.get("Position") or row.get("POS")
            number = row.get("#") or row.get("No") or row.get("Jersey")
            height_str = row.get("Ht") or row.get("Height") or row.get("HT")
            grad_year_str = row.get("Class") or row.get("Grad") or row.get("Year")

            if not player_name:
                return None

            # Split name
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

            # Parse height (format: 6-3 or 6'3" or 75)
            height_inches = None
            if height_str:
                # Format: 6-3 or 6'3"
                if "-" in height_str or "'" in height_str:
                    try:
                        parts = height_str.replace("'", "-").replace('"', "").split("-")
                        if len(parts) == 2:
                            feet = int(parts[0])
                            inches = int(parts[1])
                            height_inches = feet * 12 + inches
                    except:
                        pass
                # Format: 75 (inches)
                else:
                    height_inches = parse_int(height_str)

            # Parse grad year
            grad_year = None
            if grad_year_str:
                # Handle formats: 2025, '25, 25
                year_str = grad_year_str.replace("'", "").strip()
                if len(year_str) == 2:
                    # Convert 2-digit to 4-digit year
                    year_int = int(year_str)
                    if year_int < 50:
                        grad_year = 2000 + year_int
                    else:
                        grad_year = 1900 + year_int
                else:
                    grad_year = parse_int(year_str)

            # Create player ID
            player_id = f"npa_{player_name.lower().replace(' ', '_').replace('.', '').replace('-', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "height_inches": height_inches,
                "jersey_number": parse_int(number),
                "team_name": team_name,
                "school_country": "Canada",
                "level": PlayerLevel.PREP,
                "season": season,
                "grad_year": grad_year,
                "data_source": data_source,
            }

            # Parse season stats if available
            stats = self._parse_season_stats_from_row(row, player_id, season)
            if stats:
                player_data["season_stats"] = stats

            return self.validate_and_log_data(Player, player_data, f"player {player_name}")

        except Exception as e:
            self.logger.error("Failed to parse player from stats row", error=str(e), row=row)
            return None

    def _parse_season_stats_from_row(
        self, row: Dict[str, Any], player_id: str, season: str
    ) -> Optional[PlayerSeasonStats]:
        """Parse season stats from row."""
        try:
            # Common stat columns
            games = parse_int(row.get("GP") or row.get("G") or row.get("Games"))
            points = parse_float(row.get("PPG") or row.get("PTS") or row.get("Points"))
            rebounds = parse_float(row.get("RPG") or row.get("REB") or row.get("Rebounds"))
            assists = parse_float(row.get("APG") or row.get("AST") or row.get("Assists"))
            steals = parse_float(row.get("SPG") or row.get("STL") or row.get("Steals"))
            blocks = parse_float(row.get("BPG") or row.get("BLK") or row.get("Blocks"))
            turnovers = parse_float(row.get("TO") or row.get("TOV") or row.get("Turnovers"))
            minutes = parse_float(row.get("MPG") or row.get("MIN") or row.get("Minutes"))

            # Shooting stats
            fgm = parse_float(row.get("FGM"))
            fga = parse_float(row.get("FGA"))
            fg_pct = parse_float(row.get("FG%"))
            tpm = parse_float(row.get("3PM") or row.get("3P"))
            tpa = parse_float(row.get("3PA"))
            tp_pct = parse_float(row.get("3P%"))
            ftm = parse_float(row.get("FTM") or row.get("FT"))
            fta = parse_float(row.get("FTA"))
            ft_pct = parse_float(row.get("FT%"))

            # Additional stats
            offensive_reb_pg = parse_float(row.get("ORPG") or row.get("ORB"))
            defensive_reb_pg = parse_float(row.get("DRPG") or row.get("DRB"))
            fouls = parse_float(row.get("PF") or row.get("Fouls"))

            # Calculate rebound totals from per-game if games_played available
            offensive_reb_total = None
            defensive_reb_total = None
            if games:
                if offensive_reb_pg:
                    offensive_reb_total = int(offensive_reb_pg * games)
                if defensive_reb_pg:
                    defensive_reb_total = int(defensive_reb_pg * games)

            if not games and not points:
                return None

            stats_data = {
                "player_id": player_id,
                "season": season,
                "games_played": games,
                "minutes_per_game": minutes,
                "points_per_game": points,
                "rebounds_per_game": rebounds,
                "assists_per_game": assists,
                "steals_per_game": steals,
                "blocks_per_game": blocks,
                "turnovers_per_game": turnovers,
                "field_goal_percentage": fg_pct,
                "three_point_percentage": tp_pct,
                "free_throw_percentage": ft_pct,
                # ORB/DRB split (per-game and totals)
                "offensive_rebounds_per_game": offensive_reb_pg,
                "defensive_rebounds_per_game": defensive_reb_pg,
                "offensive_rebounds": offensive_reb_total,
                "defensive_rebounds": defensive_reb_total,
                "fouls_per_game": fouls,
            }

            return self.validate_and_log_data(
                PlayerSeasonStats, stats_data, f"season stats for {player_id}"
            )

        except Exception as e:
            self.logger.error("Failed to parse season stats", error=str(e))
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
        name = player_id.replace("npa_", "").replace("_", " ")
        season = season or self.current_season

        # Search for player and return their stats
        players = await self.search_players(
            name=name,
            season=season,
            limit=1,
        )

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
            teams_url = f"{self.teams_url}/{team_id}"
            html = await self.http_client.get_text(teams_url, cache_ttl=7200)
            soup = parse_html(html)

            # Extract team info
            team_name_elem = soup.find(["h1", "h2"], class_=lambda x: x and "team" in str(x).lower())
            team_name = get_text_or_none(team_name_elem) if team_name_elem else None

            if not team_name:
                return None

            # Extract record if available
            record_elem = soup.find(text=lambda t: t and "-" in str(t) and ("W" in str(t).upper() or "L" in str(t).upper()))
            wins, losses = None, None
            if record_elem:
                wins, losses = parse_record(record_elem)

            team_data = {
                "team_id": team_id,
                "name": team_name,
                "school": team_name,
                "level": TeamLevel.PREP,
                "season": self.current_season,
                "wins": wins,
                "losses": losses,
                "data_source": self.create_data_source_metadata(
                    url=teams_url, quality_flag=DataQualityFlag.COMPLETE
                ),
            }

            return self.validate_and_log_data(Team, team_data, f"team {team_name}")

        except Exception as e:
            self.logger.error("Failed to get team", error=str(e))
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        division: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from NPA.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            division: Division filter
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            season = season or self.current_season
            division = division or "d1"

            # Get division path
            division_path = self.DIVISIONS.get(division.lower(), "division-1")

            schedule_url = f"{self.base_url}/{division_path}/{season}/schedule"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find schedule table
            table = soup.find("table", class_=lambda x: x and ("schedule" in str(x).lower() or "game" in str(x).lower()))

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    game = self._parse_game_from_row(row, season, division, data_source)
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
        self, row: Dict[str, Any], season: str, division: str, data_source
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
                    # Try format: MM/DD/YYYY
                    if "/" in date_str:
                        month, day, year = date_str.split("/")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                    # Try ISO format: YYYY-MM-DD
                    elif "-" in date_str:
                        year, month, day = date_str.split("-")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                except Exception:
                    pass

            game_id = f"npa_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_team_id": f"npa_{home_team.lower().replace(' ', '_')}",
                "away_team_id": f"npa_{away_team.lower().replace(' ', '_')}",
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
            division: Division filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            season = season or self.current_season
            division = division or "d1"

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
