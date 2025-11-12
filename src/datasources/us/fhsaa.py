"""
FHSAA (Florida High School Athletic Association) DataSource Adapter

Provides tournament brackets, schedules, and results for Florida high school basketball.
Southeast anchor with comprehensive tournament coverage and historical data.
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


class FHSAADataSource(BaseDataSource):
    """
    Florida High School Athletic Association data source adapter.

    Provides tournament brackets, schedules, and results for Florida high school basketball.
    Major Southeast state with comprehensive tournament coverage.

    Base URL: https://www.fhsaa.com

    Strengths:
    - State championship tournaments (multiple classifications)
    - District and regional tournament brackets
    - Historical tournament data
    - Boys and girls divisions
    - Regular season schedules (district level)

    Limitations:
    - Player statistics may be limited to tournament summaries
    - Focus on team results and tournament brackets
    """

    source_type = DataSourceType.FHSAA
    source_name = "Florida High School Athletic Association"
    base_url = "https://www.fhsaa.com"
    region = DataSourceRegion.US

    def __init__(self):
        """Initialize FHSAA datasource."""
        super().__init__()

        # FHSAA URLs for basketball divisions
        self.basketball_url = f"{self.base_url}/sports/basketball"

        # Classifications in Florida: 1A, 2A, 3A, 4A, 5A, 6A, 7A
        self.classifications = ["1A", "2A", "3A", "4A", "5A", "6A", "7A"]

        self.logger.info(
            "FHSAA datasource initialized",
            base_url=self.base_url,
            coverage="Florida statewide - all classifications",
            classifications=self.classifications,
        )

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None) -> str:
        """
        Build FHSAA player ID.

        Args:
            player_name: Player name
            team_name: Optional team name for uniqueness

        Returns:
            Player ID in format: fhsaa_{name}[_{team}]
        """
        clean_name = clean_player_name(player_name).lower().replace(" ", "_")
        base_id = f"fhsaa_{clean_name}"

        if team_name:
            clean_team = clean_player_name(team_name).lower().replace(" ", "_")
            return f"{base_id}_{clean_team}"

        return base_id

    def _build_team_id(self, team_name: str, classification: Optional[str] = None) -> str:
        """
        Build FHSAA team ID.

        Args:
            team_name: Team name
            classification: Optional classification (1A-7A)

        Returns:
            Team ID in format: fhsaa_{team}[_{classification}]
        """
        clean_team = clean_player_name(team_name).lower().replace(" ", "_")
        base_id = f"fhsaa_{clean_team}"

        if classification:
            return f"{base_id}_{classification.lower()}"

        return base_id

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in FHSAA.

        Note: FHSAA focuses on tournament brackets and team results.
        Player search capabilities are limited.

        Args:
            name: Player name filter
            team: Team name filter
            season: Season year
            limit: Maximum results to return

        Returns:
            List of matching players
        """
        try:
            self.logger.info(
                "Searching FHSAA players",
                name=name,
                team=team,
                season=season,
                limit=limit,
            )

            # FHSAA doesn't have a centralized player search
            # Would need to enumerate from tournament brackets and rosters
            self.logger.warning("FHSAA player search requires roster enumeration from brackets")

            return []

        except Exception as e:
            self.logger.error(f"Error searching FHSAA players: {e}", exc_info=True)
            return []

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        FHSAA doesn't have individual player profile pages.
        Player data accessed through team rosters.

        Args:
            player_id: Player identifier

        Returns:
            None - FHSAA doesn't support direct player lookup
        """
        self.logger.warning(
            "FHSAA does not have individual player pages - use team rosters",
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

        Note: FHSAA focuses on team results and tournament brackets.
        Individual player stats typically not available.

        Args:
            player_id: Player identifier
            season: Season year

        Returns:
            None - Individual stats not typically available
        """
        self.logger.warning(
            "FHSAA focuses on team/tournament results - individual stats not available",
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
            self.logger.info("Fetching FHSAA team", team_id=team_id)

            # FHSAA team lookup would require tournament bracket parsing
            # This is a placeholder for actual implementation
            self.logger.warning("FHSAA get_team not yet fully implemented")

            return None

        except Exception as e:
            self.logger.error(f"Error fetching FHSAA team: {e}", exc_info=True)
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        gender: str = "boys",
        classification: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games from FHSAA tournament brackets and schedules.

        This is FHSAA's primary data offering - tournament brackets and results.

        Args:
            team_id: Filter by team
            start_date: Filter by start date
            end_date: Filter by end date
            season: Season year (e.g., "2024-25")
            gender: "boys" or "girls" division
            classification: Classification filter (1A-7A)
            limit: Maximum results

        Returns:
            List of games
        """
        try:
            self.logger.info(
                "Fetching FHSAA games",
                team_id=team_id,
                season=season,
                gender=gender,
                classification=classification,
                limit=limit,
            )

            # Build URL for basketball tournament page
            url = f"{self.basketball_url}/{gender}"
            if season:
                url = f"{url}?season={season}"

            # Fetch tournament page
            response = await self.http_client.get(url)

            if response.status_code != 200:
                self.logger.warning(
                    f"Failed to fetch FHSAA basketball page",
                    status_code=response.status_code,
                    url=url,
                )
                return []

            soup = parse_html(response.text)

            # Find tournament bracket or schedule tables
            # FHSAA may have multiple tables for different classifications
            tables = soup.find_all("table")

            games = []

            for table in tables:
                # Check if this is a relevant table (bracket, schedule, results)
                table_class = table.get("class", [])
                table_id = table.get("id", "")

                if not any(keyword in str(table_class) + table_id for keyword in ["bracket", "tournament", "schedule", "results"]):
                    continue

                rows = table.find_all("tr")[1:]  # Skip header

                for row in rows:
                    try:
                        cells = row.find_all(["td", "th"])
                        if len(cells) < 2:
                            continue

                        # Parse game data
                        # Format varies, but typically: Date, Home Team, Away Team, Score, Round
                        date_text = get_text_or_none(cells[0])
                        team1 = get_text_or_none(cells[1])

                        # Find second team (may be in different column positions)
                        team2 = None
                        for i in range(2, min(len(cells), 5)):
                            text = get_text_or_none(cells[i])
                            if text and text.lower() not in ["vs", "at", "@", "-"]:
                                # Check if this looks like a team name (not a score)
                                if not text.replace("-", "").isdigit():
                                    team2 = text
                                    break

                        if not team1 or not team2:
                            continue

                        # Apply team filter if specified
                        if team_id:
                            team_id_clean = clean_player_name(team_id).lower()
                            if (team_id_clean not in clean_player_name(team1).lower() and
                                team_id_clean not in clean_player_name(team2).lower()):
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
                            game_id=f"fhsaa_{self._build_team_id(team1)}_{self._build_team_id(team2)}",
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

                if len(games) >= limit:
                    break

            self.logger.info(f"Found {len(games)} FHSAA games")
            return games

        except Exception as e:
            self.logger.error(f"Error fetching FHSAA games: {e}", exc_info=True)
            return []

    async def get_leaderboard(
        self,
        stat: str = "points",
        season: Optional[str] = None,
        gender: str = "boys",
        classification: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Note: FHSAA focuses on tournament brackets and team results.
        Individual player stat leaderboards typically not available.

        Args:
            stat: Stat type (points, rebounds, assists, etc.)
            season: Season filter
            gender: "boys" or "girls" division
            classification: Classification filter (1A-7A)
            limit: Maximum results

        Returns:
            Empty list - FHSAA does not provide stat leaderboards
        """
        self.logger.warning(
            "FHSAA does not provide player stat leaderboards - tournament brackets/results only",
            stat=stat,
            season=season,
        )
        return []

    async def health_check(self) -> bool:
        """
        Check if FHSAA is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            response = await self.http_client.get(self.base_url)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"FHSAA health check failed: {e}")
            return False
