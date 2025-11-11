"""
Adidas 3SSB (3 Stripe Select Basketball) DataSource Adapter

Scrapes player and team statistics from Adidas 3SSB national circuit.
National grassroots circuit with comprehensive stats and standings.
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


class ThreeSSBDataSource(BaseDataSource):
    """
    Adidas 3SSB (3 Stripe Select Basketball) data source adapter.

    Provides access to national grassroots circuit basketball statistics.
    Official Adidas circuit with comprehensive coverage.

    Base URL: https://adidas3ssb.com
    """

    source_type = DataSourceType.THREE_SSB
    source_name = "Adidas 3SSB"
    base_url = "https://adidas3ssb.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize 3SSB datasource."""
        super().__init__()

        # Circuit-level endpoints
        self.stats_url = f"{self.base_url}/stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"
        self.teams_url = f"{self.base_url}/teams"

        self.logger.info("Adidas 3SSB datasource initialized", base_url=self.base_url)

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None) -> str:
        """
        Build 3SSB player ID.

        Args:
            player_name: Player's full name
            team_name: Optional team name for uniqueness

        Returns:
            Formatted player ID: "3ssb_{name}" or "3ssb_{name}_{team}"

        Example:
            "john_doe" -> "3ssb_john_doe"
            "john_doe", "Team Elite" -> "3ssb_john_doe_team_elite"
        """
        name_part = clean_player_name(player_name).lower().replace(" ", "_")

        if team_name:
            team_part = clean_player_name(team_name).lower().replace(" ", "_")
            return f"3ssb_{name_part}_{team_part}"

        return f"3ssb_{name_part}"

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        position: Optional[Position] = None,
        grad_year: Optional[int] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in 3SSB circuit.

        Args:
            name: Player name filter
            team: Team name filter
            position: Position filter
            grad_year: Graduation year filter
            limit: Maximum results to return

        Returns:
            List of matching players
        """
        try:
            self.logger.info(
                "Searching 3SSB players",
                name=name,
                team=team,
                position=position,
                grad_year=grad_year,
                limit=limit,
            )

            # Fetch stats page which contains player roster
            html = await self._fetch_html(self.stats_url)
            soup = parse_html(html)

            # Find player stats table
            stat_table = find_stat_table(soup, ["stats", "players", "roster"])

            if not stat_table:
                self.logger.warning("No player stats table found on 3SSB stats page")
                return []

            players = []
            rows = stat_table.find_all("tr")[1:]  # Skip header

            for row in rows:
                try:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    # Extract player data
                    player_name = get_text_or_none(cells[0])
                    if not player_name:
                        continue

                    team_name = get_text_or_none(cells[1]) if len(cells) > 1 else None
                    pos_text = get_text_or_none(cells[2]) if len(cells) > 2 else None
                    year_text = get_text_or_none(cells[3]) if len(cells) > 3 else None

                    # Apply filters
                    if name and name.lower() not in player_name.lower():
                        continue

                    if team and team_name and team.lower() not in team_name.lower():
                        continue

                    # Parse position
                    player_position = None
                    if pos_text:
                        pos_upper = pos_text.upper()
                        if "G" in pos_upper:
                            player_position = Position.GUARD
                        elif "F" in pos_upper:
                            player_position = Position.FORWARD
                        elif "C" in pos_upper:
                            player_position = Position.CENTER

                    if position and player_position != position:
                        continue

                    # Parse grad year
                    player_grad_year = parse_grad_year(year_text) if year_text else None

                    if grad_year and player_grad_year != grad_year:
                        continue

                    # Build player object
                    player = Player(
                        player_id=self._build_player_id(player_name, team_name),
                        name=player_name,
                        position=player_position,
                        team_name=team_name,
                        grad_year=player_grad_year,
                        level=PlayerLevel.GRASSROOTS,
                        data_source=self._build_source_metadata(),
                    )

                    players.append(player)

                    if len(players) >= limit:
                        break

                except Exception as e:
                    self.logger.warning(f"Error parsing player row: {e}", exc_info=True)
                    continue

            self.logger.info(f"Found {len(players)} players in 3SSB")
            return players[:limit]

        except Exception as e:
            self.logger.error(f"Error searching 3SSB players: {e}", exc_info=True)
            return []

    async def get_player_season_stats(
        self,
        player_id: str,
        season: Optional[str] = None,
    ) -> Optional[PlayerSeasonStats]:
        """
        Get season statistics for a player.

        Args:
            player_id: Player identifier (3ssb_*)
            season: Season year (e.g., "2024") - uses current if not specified

        Returns:
            PlayerSeasonStats or None
        """
        try:
            self.logger.info("Fetching 3SSB player season stats", player_id=player_id, season=season)

            # Extract player name from ID
            # Format: "3ssb_john_doe" or "3ssb_john_doe_team_elite"
            parts = player_id.replace("3ssb_", "").split("_")
            if len(parts) < 2:
                self.logger.error(f"Invalid 3SSB player_id format: {player_id}")
                return None

            # Reconstruct name (first_last format)
            player_name = " ".join(parts[:2])

            html = await self._fetch_html(self.stats_url)
            soup = parse_html(html)

            # Find stats table
            stat_table = find_stat_table(soup, ["stats", "players"])
            if not stat_table:
                return None

            rows = stat_table.find_all("tr")[1:]

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 3:
                    continue

                row_player = get_text_or_none(cells[0])
                if not row_player:
                    continue

                # Match player name
                if clean_player_name(row_player).lower() == clean_player_name(player_name).lower():
                    # Parse season stats from row
                    stats_dict = parse_season_stats_from_row(cells)

                    return PlayerSeasonStats(
                        player_id=player_id,
                        player_name=row_player,
                        season=season or str(datetime.now().year),
                        games_played=stats_dict.get("games_played", 0),
                        points_per_game=stats_dict.get("ppg", 0.0),
                        rebounds_per_game=stats_dict.get("rpg", 0.0),
                        assists_per_game=stats_dict.get("apg", 0.0),
                        steals_per_game=stats_dict.get("spg", 0.0),
                        blocks_per_game=stats_dict.get("bpg", 0.0),
                        field_goal_percentage=stats_dict.get("fg_pct", 0.0),
                        three_point_percentage=stats_dict.get("three_pct", 0.0),
                        free_throw_percentage=stats_dict.get("ft_pct", 0.0),
                        data_source=self._build_source_metadata(),
                    )

            self.logger.warning(f"Player not found in 3SSB stats: {player_name}")
            return None

        except Exception as e:
            self.logger.error(f"Error fetching 3SSB player stats: {e}", exc_info=True)
            return None

    async def get_leaderboard(
        self,
        stat_category: str = "points",
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get leaderboard for a specific stat category.

        Args:
            stat_category: Stat to rank by (points, rebounds, assists, etc.)
            season: Season year
            limit: Maximum results

        Returns:
            List of leaderboard entries with player stats
        """
        try:
            self.logger.info(
                "Fetching 3SSB leaderboard",
                stat_category=stat_category,
                season=season,
                limit=limit,
            )

            html = await self._fetch_html(self.stats_url)
            soup = parse_html(html)

            stat_table = find_stat_table(soup, ["stats", "leaders", stat_category])
            if not stat_table:
                stat_table = find_stat_table(soup, ["stats", "players"])

            if not stat_table:
                self.logger.warning("No stats table found for leaderboard")
                return []

            leaderboard = []
            rows = stat_table.find_all("tr")[1:]  # Skip header

            for idx, row in enumerate(rows[:limit], start=1):
                try:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    player_name = get_text_or_none(cells[0])
                    if not player_name:
                        continue

                    team_name = get_text_or_none(cells[1])

                    # Parse stats from row
                    stats_dict = parse_season_stats_from_row(cells)

                    entry = build_leaderboard_entry(
                        rank=idx,
                        player_id=self._build_player_id(player_name, team_name),
                        player_name=player_name,
                        team_name=team_name,
                        stat_category=stat_category,
                        stat_value=stats_dict.get(stat_category, 0.0),
                        stats_dict=stats_dict,
                    )

                    leaderboard.append(entry)

                except Exception as e:
                    self.logger.warning(f"Error parsing leaderboard row: {e}")
                    continue

            self.logger.info(f"Retrieved {len(leaderboard)} 3SSB leaderboard entries")
            return leaderboard

        except Exception as e:
            self.logger.error(f"Error fetching 3SSB leaderboard: {e}", exc_info=True)
            return []

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information and roster.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        try:
            self.logger.info("Fetching 3SSB team", team_id=team_id)

            html = await self._fetch_html(self.teams_url)
            soup = parse_html(html)

            # Find teams table
            teams_table = find_stat_table(soup, ["teams", "roster"])
            if not teams_table:
                return None

            rows = teams_table.find_all("tr")[1:]

            for row in rows:
                cells = row.find_all(["td", "th"])
                if len(cells) < 2:
                    continue

                team_name = get_text_or_none(cells[0])
                if not team_name:
                    continue

                # Match team
                team_id_normalized = clean_player_name(team_id).lower().replace(" ", "_")
                team_name_normalized = clean_player_name(team_name).lower().replace(" ", "_")

                if team_id_normalized in team_name_normalized or team_name_normalized in team_id_normalized:
                    # Extract record if available
                    record_text = get_text_or_none(cells[1]) if len(cells) > 1 else None
                    wins, losses = parse_record(record_text) if record_text else (0, 0)

                    return Team(
                        team_id=f"3ssb_{team_name_normalized}",
                        name=team_name,
                        level=TeamLevel.CLUB,
                        wins=wins,
                        losses=losses,
                        data_source=self._build_source_metadata(),
                    )

            self.logger.warning(f"Team not found: {team_id}")
            return None

        except Exception as e:
            self.logger.error(f"Error fetching 3SSB team: {e}", exc_info=True)
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 50,
    ) -> list[Game]:
        """
        Get games/schedule from 3SSB circuit.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum results

        Returns:
            List of games
        """
        try:
            self.logger.info(
                "Fetching 3SSB games",
                team_id=team_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )

            html = await self._fetch_html(self.schedule_url)
            soup = parse_html(html)

            schedule_table = find_stat_table(soup, ["schedule", "games", "matchups"])
            if not schedule_table:
                self.logger.warning("No schedule table found")
                return []

            games = []
            rows = schedule_table.find_all("tr")[1:]

            for row in rows:
                try:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    # Parse game data
                    date_text = get_text_or_none(cells[0])
                    home_team = get_text_or_none(cells[1])
                    away_team = get_text_or_none(cells[2])

                    if not home_team or not away_team:
                        continue

                    # Apply team filter
                    if team_id:
                        team_id_clean = clean_player_name(team_id).lower()
                        if (team_id_clean not in clean_player_name(home_team).lower() and
                            team_id_clean not in clean_player_name(away_team).lower()):
                            continue

                    # Parse game date
                    game_date = None
                    if date_text:
                        try:
                            from dateutil import parser
                            game_date = parser.parse(date_text)

                            # Apply date filters
                            if start_date and game_date < start_date:
                                continue
                            if end_date and game_date > end_date:
                                continue
                        except Exception:
                            pass

                    # Build game object
                    game = Game(
                        game_id=f"3ssb_{clean_player_name(home_team).lower()}_{clean_player_name(away_team).lower()}",
                        home_team=home_team,
                        away_team=away_team,
                        game_date=game_date or datetime.now(),
                        game_type=GameType.REGULAR,
                        status=GameStatus.SCHEDULED,
                        data_source=self._build_source_metadata(),
                    )

                    games.append(game)

                    if len(games) >= limit:
                        break

                except Exception as e:
                    self.logger.warning(f"Error parsing game row: {e}")
                    continue

            self.logger.info(f"Found {len(games)} 3SSB games")
            return games

        except Exception as e:
            self.logger.error(f"Error fetching 3SSB games: {e}", exc_info=True)
            return []

    async def get_player_game_stats(
        self,
        player_id: str,
        game_id: str,
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game.

        Note: 3SSB typically provides season stats, not individual game stats.
        This method returns None as game-level stats may not be available.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            None (game stats not typically available)
        """
        self.logger.warning(
            "Individual game stats not typically available for 3SSB",
            player_id=player_id,
            game_id=game_id,
        )
        return None
