"""
FEB (Federación Española de Baloncesto) DataSource Adapter

Scrapes player and game statistics from Spanish junior basketball leagues.
FEB manages multiple youth categories including U16, U18, U20 championships.

URL: https://www.feb.es
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


class FEBDataSource(BaseDataSource):
    """
    FEB (Spanish Basketball Federation) youth data source adapter.

    Provides access to Spanish junior basketball leagues:
    - Campeonato de España U16 (Under-16 Spanish Championship)
    - Campeonato de España U18 (Under-18 Spanish Championship)
    - Campeonato de España U20 (Under-20 Spanish Championship)
    - Liga EBA Junior (Junior club league)

    Coverage:
    - Player statistics and rosters
    - Championship game results
    - Regional and national tournaments
    - Statistical leaders

    Spain has one of Europe's strongest youth development systems,
    with elite academies from Real Madrid, Barcelona, Joventut, and others.
    """

    source_type = DataSourceType.FEB
    source_name = "FEB Junior"
    base_url = "https://www.feb.es"
    region = DataSourceRegion.EUROPE_ES

    # Age category mapping
    CATEGORIES = {
        "u16": "infantil",  # Spanish for U16
        "u18": "cadete",  # Spanish for U18
        "u20": "junior",  # Spanish for U20
    }

    def __init__(self):
        """Initialize FEB datasource."""
        super().__init__()

        # FEB-specific endpoints (subject to website structure)
        self.competitions_url = f"{self.base_url}/competiciones"
        self.stats_url = f"{self.base_url}/estadisticas"
        self.teams_url = f"{self.base_url}/equipos"
        self.schedule_url = f"{self.base_url}/calendario"

        # Current season (Spanish season format: YYYY-YY)
        current_year = datetime.now().year
        self.current_season = f"{current_year}-{str(current_year + 1)[-2:]}"

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID from FEB.

        Args:
            player_id: FEB player identifier (format: feb_category_firstname_lastname)

        Returns:
            Player object or None
        """
        # Extract category and name
        parts = player_id.split("_", 2)
        if len(parts) >= 3:
            category = parts[1]
            name = parts[2].replace("_", " ")
        else:
            category = "u18"
            name = player_id.replace("feb_", "").replace("_", " ")

        players = await self.search_players(name=name, category=category, limit=1)
        return players[0] if players else None

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        category: Optional[str] = None,  # "u16", "u18", "u20"
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in FEB junior leagues.

        Args:
            name: Player name (partial match)
            team: Team name (partial match)
            season: Season filter (format: 2024-25)
            category: Age category ("u16", "u18", "u20")
            limit: Maximum results

        Returns:
            List of Player objects
        """
        self.logger.info(
            "Searching FEB junior players",
            name=name,
            team=team,
            season=season,
            category=category,
        )

        try:
            season = season or self.current_season
            category = category or "u18"  # Default to U18

            # Get Spanish category name
            spanish_category = self.CATEGORIES.get(category.lower(), "junior")

            # Construct stats URL
            stats_url = f"{self.base_url}/competiciones/{spanish_category}/{season}/estadisticas"

            html = await self.http_client.get_text(stats_url, cache_ttl=7200)
            soup = parse_html(html)

            players = []
            data_source = self.create_data_source_metadata(
                url=stats_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find player stats table
            table = soup.find("table", class_=lambda x: x and ("estadisticas" in str(x).lower() or "stats" in str(x).lower()))

            if not table:
                # Try alternative selectors
                table = soup.find("table")

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    player = self._parse_player_from_stats_row(
                        row, season, category, data_source
                    )
                    if player:
                        # Apply filters
                        if name and name.lower() not in player.full_name.lower():
                            continue
                        if team and team.lower() not in (player.team_name or "").lower():
                            continue

                        players.append(player)

            self.logger.info(f"Found {len(players)} FEB junior players")
            return players

        except Exception as e:
            self.logger.error("Failed to search FEB junior players", error=str(e))
            return []

    def _parse_player_from_stats_row(
        self, row: Dict[str, Any], season: str, category: str, data_source
    ) -> Optional[Player]:
        """
        Parse player from statistics table row.

        Args:
            row: Row dictionary from stats table
            season: Season identifier
            category: Age category
            data_source: DataSource metadata

        Returns:
            Player object or None
        """
        try:
            # Common Spanish column names
            player_name = (
                row.get("Jugador")  # Spanish for "Player"
                or row.get("Nombre")  # Spanish for "Name"
                or row.get("Player")
                or row.get("NAME")
            )

            team_name = (
                row.get("Equipo")  # Spanish for "Team"
                or row.get("Club")
                or row.get("Team")
            )

            position = row.get("Pos") or row.get("Posición")
            number = row.get("#") or row.get("Dorsal")  # Spanish for "Number"

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
                # Map Spanish positions
                pos_map = {
                    "B": Position.G,  # Base (Point Guard)
                    "E": Position.SG,  # Escolta (Shooting Guard)
                    "A": Position.SF,  # Alero (Small Forward)
                    "AP": Position.PF,  # Ala-Pivot (Power Forward)
                    "P": Position.C,  # Pivot (Center)
                    "G": Position.G,
                    "F": Position.F,
                    "C": Position.C,
                }
                pos_enum = pos_map.get(pos_str)

            # Create player ID
            player_id = f"feb_{category}_{player_name.lower().replace(' ', '_').replace('.', '')}"

            # Determine level based on category
            level_map = {
                "u16": PlayerLevel.JUNIOR,
                "u18": PlayerLevel.HIGH_SCHOOL,
                "u20": PlayerLevel.PREP,
            }
            level = level_map.get(category.lower(), PlayerLevel.HIGH_SCHOOL)

            player_data = {
                "player_id": player_id,
                "first_name": first_name,
                "last_name": last_name,
                "full_name": player_name,
                "position": pos_enum,
                "jersey_number": parse_int(number),
                "team_name": team_name,
                "school_country": "Spain",
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
            # Common stat columns (Spanish and English)
            games = parse_int(row.get("PJ") or row.get("GP") or row.get("Partidos"))  # Partidos Jugados (Games Played)
            points = parse_float(row.get("Puntos") or row.get("PTS") or row.get("PPG"))
            rebounds = parse_float(row.get("Rebotes") or row.get("REB") or row.get("RPG"))
            assists = parse_float(row.get("Asistencias") or row.get("AST") or row.get("APG"))
            steals = parse_float(row.get("Robos") or row.get("STL"))
            blocks = parse_float(row.get("Tapones") or row.get("BLK"))
            turnovers = parse_float(row.get("Pérdidas") or row.get("TO"))
            minutes = parse_float(row.get("MIN") or row.get("Minutos"))

            # Shooting stats
            fgm = parse_float(row.get("TC") or row.get("FGM"))  # Tiros de Campo
            fga = parse_float(row.get("TCI") or row.get("FGA"))  # Tiros de Campo Intentados
            fg_pct = parse_float(row.get("TC%") or row.get("FG%"))
            tpm = parse_float(row.get("T3") or row.get("3PM"))  # Triples
            tpa = parse_float(row.get("T3I") or row.get("3PA"))  # Triples Intentados
            tp_pct = parse_float(row.get("T3%") or row.get("3P%"))
            ftm = parse_float(row.get("TL") or row.get("FTM"))  # Tiros Libres
            fta = parse_float(row.get("TLI") or row.get("FTA"))  # Tiros Libres Intentados
            ft_pct = parse_float(row.get("TL%") or row.get("FT%"))

            # Valoración (Spanish efficiency rating)
            efficiency = parse_float(row.get("Val") or row.get("Valoración") or row.get("EFF"))

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
        # Extract category from player_id
        parts = player_id.split("_")
        category = parts[1] if len(parts) >= 2 else "u18"
        name = "_".join(parts[2:]) if len(parts) >= 3 else player_id.replace("feb_", "")

        season = season or self.current_season

        # Search for player and return their stats
        players = await self.search_players(
            name=name.replace("_", " "),
            category=category,
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
            team_name_elem = soup.find(["h1", "h2"], class_=lambda x: x and ("equipo" in str(x).lower() or "team" in str(x).lower()))
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
        category: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from FEB junior competitions.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season filter
            category: Age category filter
            limit: Maximum results

        Returns:
            List of Game objects
        """
        try:
            season = season or self.current_season
            category = category or "u18"

            # Get Spanish category name
            spanish_category = self.CATEGORIES.get(category.lower(), "junior")

            schedule_url = f"{self.base_url}/competiciones/{spanish_category}/{season}/calendario"

            html = await self.http_client.get_text(schedule_url, cache_ttl=3600)
            soup = parse_html(html)

            games = []
            data_source = self.create_data_source_metadata(
                url=schedule_url, quality_flag=DataQualityFlag.COMPLETE
            )

            # Find schedule table
            table = soup.find("table", class_=lambda x: x and ("calendario" in str(x).lower() or "schedule" in str(x).lower()))

            if table:
                rows = extract_table_data(table)

                for row in rows[:limit]:
                    game = self._parse_game_from_row(row, season, category, data_source)
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
        self, row: Dict[str, Any], season: str, category: str, data_source
    ) -> Optional[Game]:
        """Parse game from schedule row."""
        try:
            # Spanish column names
            home_team = row.get("Local") or row.get("Home") or row.get("Equipo Local")
            away_team = row.get("Visitante") or row.get("Away") or row.get("Equipo Visitante")
            score = row.get("Resultado") or row.get("Score") or row.get("Result")
            date_str = row.get("Fecha") or row.get("Date")

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
                    # Try Spanish date format: DD/MM/YYYY
                    if "/" in date_str:
                        day, month, year = date_str.split("/")[:3]
                        game_date = datetime(int(year), int(month), int(day))
                except Exception:
                    pass

            game_id = f"feb_{category}_{home_team.lower().replace(' ', '_')}_{away_team.lower().replace(' ', '_')}"

            game_data = {
                "game_id": game_id,
                "home_team_name": home_team,
                "away_team_name": away_team,
                "home_team_id": f"feb_{home_team.lower().replace(' ', '_')}",
                "away_team_id": f"feb_{away_team.lower().replace(' ', '_')}",
                "game_date": game_date,
                "game_type": GameType.TOURNAMENT,  # Spanish championships are tournament-based
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
        category: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Args:
            stat: Stat category (points, rebounds, assists, etc.)
            season: Season filter
            category: Age category filter
            limit: Maximum results

        Returns:
            List of leaderboard entries
        """
        try:
            season = season or self.current_season
            category = category or "u18"

            # Search players to get stats
            players = await self.search_players(season=season, category=category, limit=limit * 2)

            # Build leaderboard
            leaderboard = []

            for player in players:
                if not player.season_stats:
                    continue

                stat_value = None
                if stat.lower() in ["points", "ppg", "puntos"]:
                    stat_value = player.season_stats.points_per_game
                elif stat.lower() in ["rebounds", "rpg", "rebotes"]:
                    stat_value = player.season_stats.rebounds_per_game
                elif stat.lower() in ["assists", "apg", "asistencias"]:
                    stat_value = player.season_stats.assists_per_game
                elif stat.lower() in ["steals", "spg", "robos"]:
                    stat_value = player.season_stats.steals_per_game
                elif stat.lower() in ["blocks", "bpg", "tapones"]:
                    stat_value = player.season_stats.blocks_per_game
                elif stat.lower() in ["efficiency", "valoracion"]:
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
