"""
LNB Espoirs (Ligue Nationale de Basket Espoirs) DataSource Adapter

Scrapes player and game statistics from French U21 basketball league.
LNB Espoirs is the top development league for French professional clubs.

URL: https://www.lnb.fr
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


class LNBEspoirsDataSource(BaseDataSource):
    """
    LNB Espoirs (French U21 league) data source adapter.

    Provides access to France's top youth development league:
    - Espoirs Elite (Elite U21 division)
    - Espoirs ProB (Second-tier U21 division)
    - Features youth teams from all top French pro clubs

    Coverage:
    - Player statistics and rosters
    - Game schedules and results
    - Team standings
    - Statistical leaders

    French clubs with Espoirs teams include ASVEL, Monaco, Metropolitans 92,
    Paris Basketball, Strasbourg, and other LNB pro clubs.
    """

    source_type = DataSourceType.LNB_ESPOIRS
    source_name = "LNB Espoirs"
    base_url = "https://www.lnb.fr"
    region = DataSourceRegion.EUROPE_FR

    # Division mapping
    DIVISIONS = {
        "elite": "espoirs-elite",
        "prob": "espoirs-prob",
    }

    def __init__(self):
        """Initialize LNB Espoirs datasource."""
        super().__init__()

        # LNB-specific endpoints (subject to website structure)
        self.espoirs_url = f"{self.base_url}/espoirs"
        self.stats_url = f"{self.base_url}/statistiques"  # French for "statistics"
        self.teams_url = f"{self.base_url}/equipes"  # French for "teams"
        self.schedule_url = f"{self.base_url}/calendrier"  # French for "schedule"

        # Current season (French season format: YYYY-YYYY)
        current_year = datetime.now().year
        # French season starts in September
        if datetime.now().month >= 9:
            self.current_season = f"{current_year}-{current_year + 1}"
        else:
            self.current_season = f"{current_year - 1}-{current_year}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from LNB Espoirs.

        Args:
            player_id: LNB player identifier (format: lnb_espoirs_firstname_lastname)

        Returns:
            Player object or None
        """
        # Extract name
        name = player_id.replace("lnb_espoirs_", "").replace("lnb_", "").replace("_", " ")
        players = await self.search_players(name=name, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        division: Optional[str] = None,  # "elite" or "prob"
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in LNB Espoirs.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter (format: 2024-2025)
            division: Division filter ("elite" or "prob")
            limit: Maximum results

        Returns:
            List of Player objects
        """
        self.logger.info(
            "Searching LNB Espoirs players",
            name=name,
            team=team,
            season=season,
            division=division,
        )

        try:
            season = season or self.current_season
            division = division or "elite"  # Default to Elite

            # Get French division name
            division_path = self.DIVISIONS.get(division.lower(), "espoirs-elite")

            # Construct stats URL
            stats_url = f"{self.base_url}/{division_path}/{season}/statistiques"

            html = await self.http_client.get_text(stats_url, cache_ttl=7200)
            soup = parse_html(html)

            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find player stats table
            table = soup.find("table", class_=lambda x: x and ("statistiques" in str(x).lower() or "stats" in str(x).lower()))

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

                        players.append(player)

            self.logger.info(f"Found {len(players)} LNB Espoirs players")
            return players

        except Exception as e:
            self.logger.error("Failed to search LNB Espoirs players", error=str(e))
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
            # Common French column names
            player_name = (
                row.get("Joueur")  # French for "Player"
                or row.get("Nom")  # French for "Name"
                or row.get("Player")
                or row.get("NAME")
            )

            team_name = (
                row.get("Équipe")  # French for "Team"
                or row.get("Club")
                or row.get("Team")
            )

            position = row.get("Poste") or row.get("Pos") or row.get("Position")
            number = row.get("#") or row.get("N°")  # French for "Number"
            height_str = row.get("Taille")  # French for "Height"

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
                # Map French positions
                pos_map = {
                    "MJ": Position.PG,  # Meneur de jeu (Point Guard)
                    "AR": Position.SG,  # Arrière (Shooting Guard)
                    "AI": Position.SF,  # Ailier (Small Forward)
                    "AF": Position.PF,  # Ailier fort (Power Forward)
                    "PV": Position.C,  # Pivot (Center)
                    "G": Position.G,
                    "F": Position.F,
                    "C": Position.C,
                }
                pos_enum = pos_map.get(pos_str)

            # Parse height (French format: 1m95 or 195cm)
            height_inches = None
            if height_str:
                height_cm = None
                # Format: 1m95
                if "m" in height_str:
                    try:
                        parts = height_str.replace("m", ".").replace("cm", "")
                        height_cm = int(float(parts) * 100)
                    except:
                        pass
                # Format: 195cm or 195
                else:
                    height_cm = parse_int(height_str.replace("cm", ""))

                if height_cm:
                    # Convert cm to inches (1 cm = 0.393701 inches)
                    height_inches = int(height_cm * 0.393701)

            # Create player ID
            player_id = f"lnb_espoirs_{player_name.lower().replace(' ', '_').replace('.', '').replace('-', '_')}"

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "height_inches": height_inches,
                "jersey_number": parse_int(number),
                "team_name": team_name,
                "school_country": "France",
                "level": PlayerLevel.PREP,  # U21 is typically prep level
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
            # Common stat columns (French and English)
            games = parse_int(row.get("MJ") or row.get("GP") or row.get("Matchs"))  # Matchs Joués (Games Played)
            points = parse_float(row.get("Pts") or row.get("PTS") or row.get("PPG"))
            rebounds = parse_float(row.get("Reb") or row.get("REB") or row.get("RPG"))
            assists = parse_float(row.get("Pd") or row.get("AST") or row.get("APG"))  # Passes décisives
            steals = parse_float(row.get("Int") or row.get("STL"))  # Interceptions
            blocks = parse_float(row.get("Ct") or row.get("BLK"))  # Contres
            turnovers = parse_float(row.get("Bp") or row.get("TO"))  # Balles perdues
            minutes = parse_float(row.get("Min") or row.get("MIN"))

            # Shooting stats
            fgm = parse_float(row.get("TC") or row.get("FGM"))  # Tirs au champ
            fga = parse_float(row.get("TT") or row.get("FGA"))  # Tirs tentés
            fg_pct = parse_float(row.get("TC%") or row.get("FG%"))
            tpm = parse_float(row.get("3P") or row.get("3PM"))  # 3 points
            tpa = parse_float(row.get("3T") or row.get("3PA"))  # 3 points tentés
            tp_pct = parse_float(row.get("3P%"))
            ftm = parse_float(row.get("LF") or row.get("FTM"))  # Lancers francs
            fta = parse_float(row.get("LT") or row.get("FTA"))  # Lancers francs tentés
            ft_pct = parse_float(row.get("LF%") or row.get("FT%"))

            # Evaluation (French efficiency rating)
            efficiency = parse_float(row.get("Eval") or row.get("Évaluation") or row.get("EFF"))

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
                "efficiency_rating": efficiency,
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
        name = player_id.replace("lnb_espoirs_", "").replace("_", " ")
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
            team_name_elem = soup.find(["h1", "h2"], class_=lambda x: x and ("equipe" in str(x).lower() or "team" in str(x).lower()))
            team_name = get_text_or_none(team_name_elem) if team_name_elem else None

            if not team_name:
                return None

            # Extract record if available
            record_elem = soup.find(text=lambda t: t and "-" in str(t) and ("V" in str(t).upper() or "D" in str(t).upper()))
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
        division: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from LNB Espoirs.

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
            division = division or "elite"

            # Get French division name
            division_path = self.DIVISIONS.get(division.lower(), "espoirs-elite")

            schedule_url = f"{self.base_url}/{division_path}/{season}/calendrier"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find schedule table
            table = soup.find("table", class_=lambda x: x and ("calendrier" in str(x).lower() or "schedule" in str(x).lower()))

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
            # French column names
            home_team = row.get("Domicile") or row.get("Home") or row.get("Équipe à domicile")
            away_team = row.get("Extérieur") or row.get("Away") or row.get("Équipe extérieure")
            score = row.get("Score") or row.get("Résultat")
            date_str = row.get("Date")

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
                    # Try French date format: DD/MM/YYYY
                    if "/" in date_str:
                        day, month, year = date_str.split("/")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                    # Try ISO format: YYYY-MM-DD
                    elif "-" in date_str:
                        year, month, day = date_str.split("-")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                except Exception:
                    pass

            game_id = f"lnb_espoirs_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_team_id": f"lnb_{home_team.lower().replace(' ', '_')}",
                "away_team_id": f"lnb_{away_team.lower().replace(' ', '_')}",
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
            division = division or "elite"

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
                elif stat.lower() in ["rebounds", "rpg", "reb", "rebonds"]:
                    stat_value = player.season_stats.rebounds_per_game
                elif stat.lower() in ["assists", "apg", "pd", "passes"]:
                    stat_value = player.season_stats.assists_per_game
                elif stat.lower() in ["steals", "spg", "int", "interceptions"]:
                    stat_value = player.season_stats.steals_per_game
                elif stat.lower() in ["blocks", "bpg", "ct", "contres"]:
                    stat_value = player.season_stats.blocks_per_game
                elif stat.lower() in ["efficiency", "eval", "évaluation"]:
                    stat_value = player.season_stats.efficiency_rating

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
