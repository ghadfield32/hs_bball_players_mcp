"""
Association Adapter Base

Base class for state high school athletic association adapters.
Provides common patterns for association websites that typically offer:
- Tournament brackets and schedules
- Season calendars
- Team rosters
- Championship results

Most state associations have similar structure but varying data availability.
This base class centralizes JSON discovery, calendar parsing, and bracket extraction.
"""

from abc import abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from ..models import (
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
from ..utils import get_logger, parse_html, parse_int
from ..utils.json_discovery import discover_json_endpoints, is_json_response
from .base import BaseDataSource

logger = get_logger(__name__)


class AssociationAdapterBase(BaseDataSource):
    """
    Base adapter for state high school athletic associations.

    Provides common functionality for association websites:
    - JSON-first discovery for schedules/brackets
    - HTML fallback for calendar/bracket tables
    - Season enumeration support
    - Tournament bracket parsing

    Subclasses should:
    1. Set source_type, source_name, base_url, region
    2. Implement _parse_schedule_page() or _parse_bracket_page()
    3. Optionally override _get_season_url() for season-specific URLs
    """

    # Default capabilities for association adapters
    # Override in subclass if association has stats/leaderboards
    HAS_PLAYER_STATS = False
    HAS_SCHEDULES = True
    HAS_BRACKETS = True

    def __init__(self):
        """Initialize association adapter."""
        super().__init__()
        self.seasons_cache: Dict[str, Any] = {}

    async def _fetch_with_json_discovery(
        self, url: str, keywords: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch URL and attempt JSON discovery.

        Args:
            url: URL to fetch
            keywords: Optional keywords to filter JSON endpoints

        Returns:
            Dict with keys:
                - 'json': JSON data if discovered
                - 'html': HTML content
                - 'urls': List of discovered JSON URLs
                - 'content_type': Content type
        """
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")
            result = {"url": url, "content_type": content_type}

            # If response is JSON, return it
            if is_json_response(content_type):
                try:
                    result["json"] = response.json()
                    result["html"] = ""
                    result["urls"] = []
                    logger.info(f"Fetched JSON response", url=url)
                    return result
                except Exception as e:
                    logger.warning(f"Failed to parse JSON response", url=url, error=str(e))

            # Otherwise, it's HTML - discover embedded JSON endpoints
            html = response.text
            result["html"] = html
            result["urls"] = discover_json_endpoints(html, url)

            # Try to fetch first discovered JSON endpoint
            if result["urls"]:
                if keywords:
                    # Filter by keywords if provided
                    from ..utils.json_discovery import filter_json_by_keywords

                    filtered = filter_json_by_keywords(result["urls"], keywords)
                    result["urls"] = filtered

                # Try first URL
                if result["urls"]:
                    first_json_url = result["urls"][0]
                    try:
                        json_response = await self.http_client.get(first_json_url)
                        if is_json_response(json_response.headers.get("content-type", "")):
                            result["json"] = json_response.json()
                            logger.info(
                                f"Fetched discovered JSON endpoint",
                                url=first_json_url,
                            )
                    except Exception as e:
                        logger.debug(
                            f"Failed to fetch discovered JSON",
                            url=first_json_url,
                            error=str(e),
                        )

            return result

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching URL", url=url, status=e.response.status_code)
            raise
        except Exception as e:
            logger.error(f"Error fetching URL", url=url, error=str(e))
            raise

    async def get_season_data(self, season: Optional[str] = None) -> Dict[str, Any]:
        """
        Get data for a specific season.

        Args:
            season: Season string (e.g., '2024-25'), None for current

        Returns:
            Dict with season data (schedules, teams, games, etc.)
        """
        season = season or self._get_current_season()

        # Check cache
        if season in self.seasons_cache:
            logger.debug(f"Using cached season data", season=season)
            return self.seasons_cache[season]

        # Fetch season data
        season_url = self._get_season_url(season)
        data = await self._fetch_with_json_discovery(
            season_url, keywords=["schedule", "bracket", "calendar", "tournament"]
        )

        # Parse data based on what we received
        if "json" in data and data["json"]:
            result = await self._parse_json_data(data["json"], season)
        else:
            result = await self._parse_html_data(data["html"], season)

        # Cache result
        self.seasons_cache[season] = result
        return result

    def _get_season_url(self, season: str) -> str:
        """
        Get URL for specific season data.

        Override this in subclass if association has season-specific URLs.

        Args:
            season: Season string (e.g., '2024-25')

        Returns:
            URL for season data
        """
        # Default: use base URL with season parameter
        return f"{self.base_url}/sports/basketball?season={season}"

    def _get_current_season(self) -> str:
        """
        Get current season string.

        Returns:
            Current season in format 'YYYY-YY' (e.g., '2024-25')
        """
        now = datetime.now()
        if now.month >= 8:  # Season starts in August/September
            return f"{now.year}-{str(now.year + 1)[-2:]}"
        else:
            return f"{now.year - 1}-{str(now.year)[-2:]}"

    @abstractmethod
    async def _parse_json_data(self, json_data: Dict[str, Any], season: str) -> Dict[str, Any]:
        """
        Parse JSON data from association.

        Override in subclass to handle association-specific JSON structure.

        Args:
            json_data: JSON data from endpoint
            season: Season string

        Returns:
            Dict with parsed data (teams, games, etc.)
        """
        pass

    @abstractmethod
    async def _parse_html_data(self, html: str, season: str) -> Dict[str, Any]:
        """
        Parse HTML data from association.

        Override in subclass to handle association-specific HTML structure.

        Args:
            html: HTML content
            season: Season string

        Returns:
            Dict with parsed data (teams, games, etc.)
        """
        pass

    # BaseDataSource required methods with default implementations

    async def get_player(self, player_id: str) -> Optional[Player]:
        """
        Get player by ID.

        Most associations don't have player profiles.
        Override if association provides player data.
        """
        logger.warning(
            f"Association {self.source_name} does not support player profiles",
            source=self.source_name,
        )
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

        Most associations don't provide searchable player data.
        Override if association has player search.
        """
        logger.warning(
            f"Association {self.source_name} does not support player search",
            source=self.source_name,
        )
        return []

    async def get_player_season_stats(
        self, player_id: str, season: Optional[str] = None
    ) -> Optional[PlayerSeasonStats]:
        """
        Get player season stats.

        Most associations don't track player stats.
        Override if association provides player statistics.
        """
        logger.warning(
            f"Association {self.source_name} does not provide player statistics",
            source=self.source_name,
        )
        return None

    async def get_player_game_stats(
        self, player_id: str, game_id: str
    ) -> Optional[PlayerGameStats]:
        """
        Get player game stats.

        Most associations don't have game-level player stats.
        Override if association provides box scores.
        """
        logger.warning(
            f"Association {self.source_name} does not provide box scores",
            source=self.source_name,
        )
        return None

    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get team by ID.

        Delegates to season data parsing.
        """
        season_data = await self.get_season_data()
        teams = season_data.get("teams", [])

        for team in teams:
            if team.team_id == team_id:
                return team

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
        Get games with optional filters.

        Delegates to season data parsing.
        """
        season_data = await self.get_season_data(season)
        games = season_data.get("games", [])

        # Apply filters
        if team_id:
            games = [g for g in games if g.home_team_id == team_id or g.away_team_id == team_id]

        if start_date:
            games = [g for g in games if g.game_date and g.game_date >= start_date]

        if end_date:
            games = [g for g in games if g.game_date and g.game_date <= end_date]

        return games[:limit]

    async def get_leaderboard(
        self,
        stat: str,
        season: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """
        Get statistical leaderboard.

        Most associations don't provide leaderboards.
        Override if association has stat leaders.
        """
        logger.warning(
            f"Association {self.source_name} does not provide leaderboards",
            source=self.source_name,
        )
        return []
