"""
RankOne Sport DataSource Adapter

Provides schedules, fixtures, and rosters for multiple US states.
Multi-state platform covering TX, KY, IN, OH, TN.
Focus: Schedules and fixtures (no player stats typically available).
Used as entity resolution layer - team names, schedules, rosters.
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


class RankOneDataSource(BaseDataSource):
    """
    RankOne Sport data source adapter.

    Provides schedules, fixtures, and roster data across multiple states.
    District-based structure for managing school athletics.

    Supported States:
        - TX: Texas
        - KY: Kentucky
        - IN: Indiana
        - OH: Ohio
        - TN: Tennessee

    Base URL: https://www.rankonesport.com

    Note: RankOne typically provides schedules/rosters but NOT player statistics.
    Use this adapter for entity resolution (team names, schedules) and fixtures.
    """

    source_type = DataSourceType.RANKONE
    source_name = "RankOne Sport"
    base_url = "https://www.rankonesport.com"
    region = DataSourceRegion.US

    # Multi-state support
    SUPPORTED_STATES = ["TX", "KY", "IN", "OH", "TN"]

    # State full names for metadata
    STATE_NAMES = {
        "TX": "Texas",
        "KY": "Kentucky",
        "IN": "Indiana",
        "OH": "Ohio",
        "TN": "Tennessee",
    }

    def __init__(self):
        """Initialize RankOne datasource with multi-state support."""
        super().__init__()

        self.logger.info(
            f"RankOne initialized with {len(self.SUPPORTED_STATES)} states",
            states=self.SUPPORTED_STATES,
        )

    def _validate_state(self, state: Optional[str]) -> str:
        """
        Validate and normalize state parameter.

        Args:
            state: State code (TX, KY, IN, OH, TN)

        Returns:
            Uppercase state code

        Raises:
            ValueError: If state is invalid or not supported
        """
        if not state:
            raise ValueError(
                f"State parameter required. Supported states: {', '.join(self.SUPPORTED_STATES)}"
            )

        state = state.upper().strip()

        if state not in self.SUPPORTED_STATES:
            raise ValueError(
                f"State '{state}' not supported. Supported states: {', '.join(self.SUPPORTED_STATES)}"
            )

        return state

    def _build_player_id(self, state: str, player_name: str, team_name: Optional[str] = None) -> str:
        """
        Build RankOne player ID with state prefix.

        Args:
            state: State code
            player_name: Player name
            team_name: Optional team name for uniqueness

        Returns:
            Player ID in format: rankone_{state}_{name}[_{team}]

        Example:
            _build_player_id("TX", "John Doe") -> "rankone_tx_john_doe"
            _build_player_id("TX", "John Doe", "Austin HS") -> "rankone_tx_john_doe_austin_hs"
        """
        clean_name = clean_player_name(player_name).lower().replace(" ", "_")
        base_id = f"rankone_{state.lower()}_{clean_name}"

        if team_name:
            clean_team = clean_player_name(team_name).lower().replace(" ", "_")
            return f"{base_id}_{clean_team}"

        return base_id

    def _build_team_id(self, state: str, team_name: str) -> str:
        """
        Build RankOne team ID.

        Args:
            state: State code
            team_name: Team name

        Returns:
            Team ID in format: rankone_{state}_{team}
        """
        clean_team = clean_player_name(team_name).lower().replace(" ", "_")
        return f"rankone_{state.lower()}_{clean_team}"

    async def search_players(
        self,
        name: Optional[str] = None,
        team: Optional[str] = None,
        state: Optional[str] = None,
        limit: int = 50,
    ) -> list[Player]:
        """
        Search for players in RankOne rosters.

        Note: RankOne primarily provides rosters through team pages.
        Player search is limited to roster listings.

        Args:
            name: Player name filter
            team: Team name filter
            state: State code (required for RankOne)
            limit: Maximum results to return

        Returns:
            List of matching players
        """
        try:
            if not state:
                self.logger.warning("State parameter required for RankOne search")
                return []

            state = self._validate_state(state)

            self.logger.info(
                "Searching RankOne rosters",
                name=name,
                team=team,
                state=state,
                limit=limit,
            )

            # RankOne doesn't have a direct player search
            # Would need to enumerate teams first, then fetch rosters
            # For now, return empty list with warning
            self.logger.warning(
                "RankOne search_players requires team enumeration - not yet implemented"
            )
            return []

        except Exception as e:
            self.logger.error(f"Error searching RankOne players: {e}", exc_info=True)
            return []

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        RankOne doesn't have individual player profile pages.
        Player data is accessed through team rosters.

        Args:
            player_id: Player identifier (format: rankone_{state}_{name})

        Returns:
            None - RankOne doesn't support direct player lookup
        """
        self.logger.warning(
            "RankOne does not support direct player lookup - use team rosters",
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

        Note: RankOne typically does NOT provide player statistics.
        This adapter is for schedules/fixtures only.

        Args:
            player_id: Player identifier
            season: Season year

        Returns:
            None - RankOne does not provide player stats
        """
        self.logger.warning(
            "RankOne does not provide player statistics - schedules/fixtures only",
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

        Note: RankOne does NOT provide player statistics.

        Args:
            player_id: Player identifier
            game_id: Game identifier

        Returns:
            None - RankOne does not provide player stats
        """
        return None

    async def get_team(self, team_id: str, state: Optional[str] = None) -> Optional[Team]:
        """
        Get team information by ID.

        Args:
            team_id: Team identifier
            state: State code (helps with lookup)

        Returns:
            Team object or None
        """
        try:
            self.logger.info("Fetching RankOne team", team_id=team_id, state=state)

            # RankOne team lookup would require knowing district/school ID
            # This is a placeholder for the actual implementation
            self.logger.warning("RankOne get_team not yet fully implemented")

            return None

        except Exception as e:
            self.logger.error(f"Error fetching RankOne team: {e}", exc_info=True)
            return None

    async def get_games(
        self,
        team_id: Optional[str] = None,
        state: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        season: Optional[str] = None,
        limit: int = 100,
    ) -> list[Game]:
        """
        Get games/schedule data.

        This is RankOne's primary data offering - schedules and fixtures.

        Args:
            team_id: Filter by team
            state: State code (helps narrow search)
            start_date: Filter by start date
            end_date: Filter by end date
            season: Filter by season
            limit: Maximum results

        Returns:
            List of games
        """
        try:
            self.logger.info(
                "Fetching RankOne games",
                team_id=team_id,
                state=state,
                season=season,
                limit=limit,
            )

            # RankOne schedule lookup requires team/district context
            # This is a placeholder for actual implementation
            self.logger.warning("RankOne get_games not yet fully implemented")

            return []

        except Exception as e:
            self.logger.error(f"Error fetching RankOne games: {e}", exc_info=True)
            return []

    async def health_check(self) -> bool:
        """
        Check if RankOne is accessible.

        Returns:
            True if accessible, False otherwise
        """
        try:
            response = await self.http_client.get(self.base_url)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"RankOne health check failed: {e}")
            return False
