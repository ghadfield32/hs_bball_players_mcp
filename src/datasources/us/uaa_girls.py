"""
UAA Girls / UA Next DataSource Adapter

Extends the boys UAA adapter for girls basketball statistics.
Reuses all scraping logic from the base UAA adapter with girls-specific URLs.

UA Next is the girls division of the Under Armour Association.
"""

from datetime import datetime
from typing import Optional

from ...models import DataSourceRegion, DataSourceType
from .uaa import UAADataSource


class UAAGirlsDataSource(UAADataSource):
    """
    UAA Girls / UA Next data source adapter.

    Extends UAADataSource with girls-specific configuration.
    All scraping methods are inherited - only URLs and ID prefixes differ.

    UA Next is the official girls division of the Under Armour Association.
    Public stats pages at https://uanext.com or https://underarmourassociation.com/girls
    """

    source_type = DataSourceType.UAA_GIRLS
    source_name = "UA Next (Girls UAA)"
    base_url = "https://uanext.com"  # May also be underarmourassociation.com/girls
    region = DataSourceRegion.US

    def __init__(self):
        """
        Initialize UAA Girls / UA Next datasource.

        Inherits all methods from UAADataSource parent class.
        Only overrides URLs and ID prefix to point to girls section.
        """
        # Call parent init which sets up HTTP client, rate limiter, logger
        super().__init__()

        # Override UAA-specific endpoints for girls section
        # UA Next may use separate domain or /girls path - check both
        self.stats_url = f"{self.base_url}/stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"
        self.teams_url = f"{self.base_url}/teams"
        self.events_url = f"{self.base_url}/events"

        self.logger.info(
            f"Initialized {self.source_name}",
            base_url=self.base_url,
            endpoints={
                "stats": self.stats_url,
                "schedule": self.schedule_url,
                "standings": self.standings_url,
                "teams": self.teams_url,
                "events": self.events_url,
            },
        )

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None, season: Optional[str] = None) -> str:
        """
        Build UAA Girls player ID with namespace prefix.

        Overrides parent to use girls-specific prefix to avoid ID collisions.

        Args:
            player_name: Player's full name
            team_name: Optional team name for uniqueness
            season: Optional season for uniqueness

        Returns:
            Formatted player ID: "uaa_g:{name}" or "uaa_g:{name}:{team}:{season}"

        Example:
            "jane_doe" -> "uaa_g:jane_doe"
            "jane_doe", "Team Elite", "2024" -> "uaa_g:jane_doe:team_elite:2024"
        """
        from ...utils import clean_player_name

        name_part = clean_player_name(player_name).lower().replace(" ", "_")

        parts = [f"uaa_g:{name_part}"]

        if team_name:
            team_part = clean_player_name(team_name).lower().replace(" ", "_")
            parts.append(team_part)

        if season:
            parts.append(season)

        return ":".join(parts)

    def _build_team_id(self, team_name: str, division: Optional[str] = None) -> str:
        """
        Build UAA Girls team ID.

        Overrides parent to use girls-specific prefix.

        Args:
            team_name: Team name
            division: Optional division (15U, 16U, 17U)

        Returns:
            Formatted team ID: "uaa_g:team_{name}" or "uaa_g:team_{name}_{division}"
        """
        from ...utils import clean_player_name

        team_part = clean_player_name(team_name).lower().replace(" ", "_")

        if division:
            return f"uaa_g:team_{team_part}_{division.lower()}"

        return f"uaa_g:team_{team_part}"


# Note: All methods (search_players, get_player_season_stats, get_leaderboard, etc.)
# are inherited from UAADataSource and work identically.
# The only differences are:
# 1. base_url which changes all endpoint URLs
# 2. _build_player_id which uses "uaa_g:" prefix instead of "uaa:"
# 3. _build_team_id which uses "uaa_g:team_" prefix
#
# This design is efficient because:
# 1. No code duplication - reuses all scraping logic
# 2. Maintains consistency between boys and girls adapters
# 3. Easy to maintain - bug fixes to UAA apply to both
# 4. Minimal overhead - just URL configuration and ID prefix differences
# 5. ID namespace separation prevents boys/girls player collisions
#
# Usage:
#     uaa_girls = UAAGirlsDataSource()
#     players = await uaa_girls.search_players(name="Smith", division="17U", limit=10)
#     leaders = await uaa_girls.get_leaderboard("points", limit=25)
