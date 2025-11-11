"""
NBBL (Nachwuchs Basketball Bundesliga) DataSource Adapter

Scrapes player and game statistics from German youth basketball leagues.
NBBL (U19) and JBBL (U16) are the top youth leagues in Germany.

URL: https://www.nbbl-basketball.de
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


class NBBLDataSource(BaseDataSource):
    """
    NBBL/JBBL (German youth basketball) data source adapter.

    Provides access to player stats, team rosters, and game data from:
    - NBBL (Nachwuchs Basketball Bundesliga) - U19 league
    - JBBL (Jugend Basketball Bundesliga) - U16 league

    Coverage:
    - Player statistics and rosters
    - Game schedules and results
    - Team standings
    - League-wide statistical leaders

    German youth basketball is highly competitive with strong club academies
    from Bayern Munich, Alba Berlin, Ratiopharm Ulm, and other pro clubs.
    """

    source_type = DataSourceType.NBBL
    source_name = "NBBL/JBBL"
    base_url = "https://www.nbbl-basketball.de"
    region = DataSourceRegion.EUROPE_DE

    def __init__(self):
        """Initialize NBBL datasource."""
        super().__init__()

        # NBBL-specific endpoints (subject to website structure)
        self.nbbl_url = f"{self.base_url}/nbbl"  # U19 league
        self.jbbl_url = f"{self.base_url}/jbbl"  # U16 league
        self.stats_url = f"{self.base_url}/statistiken"  # German for "statistics"
        self.teams_url = f"{self.base_url}/teams"
        self.schedule_url = f"{self.base_url}/spielplan"  # German for "schedule"

        # Current season (German season format: YYYY/YY)
        current_year = datetime.now().year
        self.current_season = f"{current_year}/{str(current_year + 1)[-2:]}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from NBBL/JBBL.

        Args:
            player_id: NBBL player identifier (format: nbbl_firstname_lastname or jbbl_firstname_lastname)

        Returns:
            Player object or None
        """
        # Search for player by name
        name = player_id.replace("nbbl_", "").replace("jbbl_", "").replace("_", " ")
        players = await self.search_players(name=name, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        league: Optional[str] = None,  # "nbbl" or "jbbl"
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in NBBL/JBBL.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter (format: 2024/25)
            league: League filter ("nbbl" or "jbbl")
            limit: Maximum results

        Returns:
            List of Player objects
        """
        self.logger.info(
            "Searching NBBL/JBBL players",
            name=name,
            team=team,
            season=season,
            league=league,
        )

        try:
            season = season or self.current_season
            league = league or "nbbl"  # Default to NBBL (U19)

            # Construct stats URL
            stats_url = f"{self.base_url}/{league}/statistiken/{season.replace('/', '-')}"

            html = await self.http_client.get_text(stats_url, cache_ttl=7200)
            soup = parse_html(html)

            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find player stats table
            table = soup.find("table", class_=lambda x: x and ("stats" in str(x).lower() or "spieler" in str(x).lower()))

            if not table:
                # Try alternative selectors
                table = soup.find("table")

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    player = self._parse_player_from_stats_row(
                        row, season, league, data_source
                    )
                    if player:
                        # Apply filters
                        if name and name.lower() not in player.full_name.lower():
                            continue
                        if team and team.lower() not in (player.team_name or "").lower():
                            continue

                        players.append(player)

            self.logger.info(f"Found {len(players)} NBBL/JBBL players")
            return players

        except Exception as e:
            self.logger.error("Failed to search NBBL/JBBL players", error=str(e))
            return []

    def _parse_player_from_stats_row(
        self, row: Dict[str, Any], season: str, league: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from statistics table row.

        Args:
            row: Row dictionary from stats table
            season: Season identifier
            league: League identifier ("nbbl" or "jbbl")
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Common German column names
            player_name = (
                row.get("Spieler")  # German for "Player"
                or row.get("Name")
                or row.get("Player")
                or row.get("NAME")
            )

            team_name = (
                row.get("Team")
                or row.get("Verein")  # German for "Club"
                or row.get("Mannschaft")  # German for "Team"
            )

            position = row.get("Pos") or row.get("Position")
            number = row.get("#") or row.get("Nr")  # German for "Number"

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
                pos_str = position.upper().strip()
                # Map German positions
                pos_map = {
                    "F": Position.F,
                    "G": Position.G,
                    "C": Position.C,
                    "PG": Position.PG,
                    "SG": Position.SG,
                    "SF": Position.SF,
                    "PF": Position.PF,
                }
                pos_enum = pos_map.get(pos_str)

            # Create player ID
            league_prefix = league.lower()
            player_id = f"{league_prefix}_{player_name.lower().replace(' ', '_').replace('.', '')}"

            # Determine level based on league
            level = PlayerLevel.JUNIOR if league.lower() == "jbbl" else PlayerLevel.HIGH_SCHOOL

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "jersey_number": parse_int(number),
                "team_name": team_name,
                "school_country": "Germany",
                "level": level,
                "season": season,
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
            # Common stat columns (German)
            games = parse_int(row.get("Spiele") or row.get("GP") or row.get("G"))  # Games
            points = parse_float(row.get("Punkte") or row.get("PTS") or row.get("PPG"))
            rebounds = parse_float(row.get("Rebounds") or row.get("REB") or row.get("RPG"))
            assists = parse_float(row.get("Assists") or row.get("AST") or row.get("APG"))
            steals = parse_float(row.get("Steals") or row.get("STL"))
            blocks = parse_float(row.get("Blocks") or row.get("BLK"))
            turnovers = parse_float(row.get("TO") or row.get("Turnover"))
            minutes = parse_float(row.get("MIN") or row.get("Minuten"))

            # Shooting stats
            fgm = parse_float(row.get("FGM") or row.get("2P"))
            fga = parse_float(row.get("FGA"))
            fg_pct = parse_float(row.get("FG%"))
            tpm = parse_float(row.get("3PM") or row.get("3P"))
            tpa = parse_float(row.get("3PA"))
            tp_pct = parse_float(row.get("3P%"))
            ftm = parse_float(row.get("FTM") or row.get("FT"))
            fta = parse_float(row.get("FTA"))
            ft_pct = parse_float(row.get("FT%"))

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
        # Extract league from player_id
        league = "nbbl" if player_id.startswith("nbbl_") else "jbbl"
        season = season or self.current_season

        # Search for player and return their stats
        players = await self.search_players(
            name=player_id.replace(f"{league}_", "").replace("_", " "),
            league=league,
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
            record_elem = soup.find(text=lambda t: t and "-" in str(t) and "W" in str(t).upper())
            wins, losses = None, None
            if record_elem:
                wins, losses = parse_record(record_elem)

            team_data = {
                "team_id": team_id,
                "name": team_name,
                "school": team_name,
                "level": TeamLevel.CLUB,
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
        league: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from NBBL/JBBL.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            league: League filter ("nbbl" or "jbbl")
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            season = season or self.current_season
            league = league or "nbbl"

            schedule_url = f"{self.base_url}/{league}/spielplan/{season.replace('/', '-')}"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find schedule table
            table = soup.find("table", class_=lambda x: x and ("schedule" in str(x).lower() or "spielplan" in str(x).lower()))

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    game = self._parse_game_from_row(row, season, league, data_source)
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
        self, row: Dict[str, Any], season: str, league: str, data_source
    ) -> Optional[Game]:
        """Parse game from schedule row."""
        try:
            home_team = row.get("Heim") or row.get("Home") or row.get("Home Team")
            away_team = row.get("Gast") or row.get("Away") or row.get("Away Team")
            score = row.get("Ergebnis") or row.get("Score") or row.get("Result")
            date_str = row.get("Datum") or row.get("Date")

            if not home_team or not away_team:
                return None

            # Parse score
            home_score, away_score = None, None
            status = GameStatus.SCHEDULED

            if score and ":" in score:
                parts = score.split(":")
                if len(parts) == 2:
                    home_score = parse_int(parts[0].strip())
                    away_score = parse_int(parts[1].strip())
                    if home_score is not None and away_score is not None:
                        status = GameStatus.COMPLETED

            # Parse date
            game_date = None
            if date_str:
                try:
                    # Try German date format: DD.MM.YYYY
                    if "." in date_str:
                        day, month, year = date_str.split(".")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                except Exception:
                    pass

            game_id = f"{league}_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_team_id": f"{league}_{home_team.lower().replace(' ', '_')}",
                "away_team_id": f"{league}_{away_team.lower().replace(' ', '_')}",
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
        league: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category (points, rebounds, assists, etc.)
            season: Season filter
            league: League filter ("nbbl" or "jbbl")
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            season = season or self.current_season
            league = league or "nbbl"

            # Search players to get stats
            players = await self.search_players(season=season, league=league, limit=limit * 2)

            # Build leaderboard
            leaderboard = []

            for player in players:
                if not player.season_stats:
                    continue

                stat_value = None
                if stat.lower() in ["points", "ppg"]:
                    stat_value = player.season_stats.points_per_game
                elif stat.lower() in ["rebounds", "rpg"]:
                    stat_value = player.season_stats.rebounds_per_game
                elif stat.lower() in ["assists", "apg"]:
                    stat_value = player.season_stats.assists_per_game
                elif stat.lower() in ["steals", "spg"]:
                    stat_value = player.season_stats.steals_per_game
                elif stat.lower() in ["blocks", "bpg"]:
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
