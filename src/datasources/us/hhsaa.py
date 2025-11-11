"""
HHSAA (Hawaii High School Athletic Association) DataSource Adapter

Provides tournament brackets, schedules, and historical data for Hawaii high school basketball.
Excellent historical coverage with tournament brackets and records dating back multiple years.
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
    find_stat_table,
    parse_grad_year,
)
from ..base import BaseDataSource


class HHSAADataSource(BaseDataSource):
    """
    Hawaii High School Athletic Association data source adapter.

    Provides tournament brackets, schedules, and results for Hawaii high school basketball.
    Strong historical coverage with multi-year tournament data.

    Base URL: https://www.hhsaa.org

    Strengths:
    - Excellent tournament bracket coverage
    - Historical data (multiple years available)
    - Boys and girls divisions
    - State championship brackets
    - Regular season schedules via OIA and other leagues

    Limitations:
    - Player statistics may be limited
    - Focus is on team/game results rather than individual stats
    """

    source_type = DataSourceType.HHSAA
    source_name = "Hawaii High School Athletic Association"
    base_url = "https://www.hhsaa.org"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize HHSAA datasource."""
        super().__init__()

        # HHSAA URLs for different sports/divisions
        self.basketball_boys_url = f"{self.base_url}/sports/basketball_boys"
        self.basketball_girls_url = f"{self.base_url}/sports/basketball_girls"

        self.logger.info(
            "HHSAA datasource initialized",
            base_url=self.base_url,
            coverage="Hawaii statewide - tournament brackets and schedules",
        )

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None) -> str:
        """
        Build HHSAA player ID.

        Args:
            player_name: Player name
            team_name: Optional team name for uniqueness

        Returns:
            Player ID in format: hhsaa_{name}[_{team}]
        """
        clean_name = clean_player_name(player_name).lower().replace(" ", "_")
        base_id = f"hhsaa_{clean_name}"

        if team_name:
            clean_team = clean_player_name(team_name).lower().replace(" ", "_")
            return f"{base_id}_{clean_team}"

        return base_id

    def _build_team_id(self, team_name: str) -> str:
        """
        Build HHSAA team ID.

        Args:
            team_name: Team name

        Returns:
            Team ID in format: hhsaa_{team}
        """
        clean_team = clean_player_name(team_name).lower().replace(" ", "_")
        return f"hhsaa_{clean_team}"

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in HHSAA.

        Note: HHSAA focuses on team/tournament data.
        Player search capabilities may be limited.

        Args:
            name: Player name filter
            team: Team name filter
            season: Season year (e.g., "2024")
            limit: Maximum results to return

        Returns:
            List of matching players
        """
        try:
            self.logger.info(
                "Searching HHSAA players",
                name=name,
                team=team,
                season=season,
                limit=limit,
            )

            # HHSAA doesn't have a direct player search interface
            # Would need to enumerate rosters from tournament brackets
            self.logger.warning("HHSAA player search requires roster enumeration from brackets")

            return []

        except Exception as e:
            self.logger.error(f"Error searching HHSAA players: {e}", exc_info=True)
            return []

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        HHSAA doesn't have individual player profile pages.
        Player data accessed through team rosters and tournament brackets.

        Args:
            player_id: Player identifier

        Returns:
            None - HHSAA doesn't support direct player lookup
        """
        self.logger.warning(
            "HHSAA does not have individual player pages - use team rosters",
            player_id=player_id,
        )
        return None

    async def get_player_season_stats(
        self,
        player_id: str,
        season: Optional[str] = None,
    ) -> Optional[PlayerSeasonStats]:
        """
        Get season statistics for a player.

        Note: HHSAA typically focuses on team results rather than individual player stats.

        Args:
            player_id: Player identifier
            season: Season year

        Returns:
            None - Individual stats not typically available
        """
        self.logger.warning(
            "HHSAA focuses on team results - individual player stats may not be available",
            player_id=player_id,
        )
        return None

    async def get_player_game_stats(
        self,
        player_id: str,
        game_id: str,
    ) -> Optional[PlayerGameStats]:
        """
        Get player statistics for a specific game.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            None - Individual game stats not typically available
        """
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team information by ID.

        Args:
            team_id: Team identifier

        Returns:
            Team object or None
        """
        try:
            self.logger.info("Fetching HHSAA team", team_id=team_id)

            # HHSAA team lookup would require tournament bracket parsing
            # This is a placeholder for actual implementation
            self.logger.warning("HHSAA get_team not yet fully implemented")

            return None

        except Exception as e:
            self.logger.error(f"Error fetching HHSAA team: {e}", exc_info=True)
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        gender: str = "boys",
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from HHSAA tournament brackets and schedules.

        This is HHSAA's primary data offering - tournament brackets and results.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season year (e.g., "2024")
            gender: "boys" or "girls" division
            limit: Maximum results

        Returns:
            List of games
        """
        try:
            self.logger.info(
                "Fetching HHSAA games",
                team_id=team_id,
                season=season,
                gender=gender,
                limit=limit,
            )

            # Determine base URL based on gender
            if gender.lower() == "girls":
                base_url = self.basketball_girls_url
            else:
                base_url = self.basketball_boys_url

            # Add season parameter if provided
            if season:
                url = f"{base_url}/tournament/{season}"
            else:
                url = f"{base_url}/tournament"

            # Fetch tournament bracket page
            response = await self.http_client.get(url)

            if response.status_code != 200:
                self.logger.warning(
                    f"Failed to fetch HHSAA tournament page",
                    status_code=response.status_code,
                    url=url,
                )
                return []

            soup = parse_html(response.text)

            # Find tournament bracket or schedule table
            bracket_table = find_stat_table(soup, ["bracket", "tournament", "schedule", "games"])

            if not bracket_table:
                self.logger.warning("No tournament bracket found on HHSAA page")
                return []

            games = []
            rows = bracket_table.find_all("tr")[1:]  # Skip header

            for row in rows:
                try:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 3:
                        continue

                    # Parse game data from bracket
                    # Typical format: Date | Team1 | Score | Team2 | Round
                    date_text = get_text_or_none(cells[0])
                    team1 = get_text_or_none(cells[1])
                    team2 = get_text_or_none(cells[3]) if len(cells) > 3 else None

                    if not team1 or not team2:
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
                        game_id=f"hhsaa_{self._build_team_id(team1)}_{self._build_team_id(team2)}",
                        home_team=team1,
                        away_team=team2,
                        game_date=game_date or datetime.now(),
                        game_type=GameType.TOURNAMENT,
                        status=GameStatus.FINAL if game_date and game_date < datetime.now() else GameStatus.SCHEDULED,
                        data_source=self.create_data_source_metadata(url=url),
                    )

                    games.append(game)

                    if len(games) >= limit:
                        break

                except Exception as e:
                    self.logger.warning(f"Error parsing game row: {e}")
                    continue

            self.logger.info(f"Found {len(games)} HHSAA games")
            return games

        except Exception as e:
            self.logger.error(f"Error fetching HHSAA games: {e}", exc_info=True)
            return []

    async def health_check(self) -> bool:
        """
        Check if HHSAA is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            response = await self.http_client.get(self.base_url)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"HHSAA health check failed: {e}")
            return False
