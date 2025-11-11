"""
Adidas 3SSB Girls (3 Stripe Select Basketball) DataSource Adapter

Extends the boys 3SSB adapter for girls basketball statistics.
Reuses all scraping logic from the base 3SSB adapter with girls-specific URLs.
"""

from datetime import datetime
from typing import Optional

from ...models import DataSourceRegion, DataSourceType
from .three_ssb import ThreeSSBDataSource


class ThreeSSBGirlsDataSource(ThreeSSBDataSource):
    """
    Adidas 3SSB Girls data source adapter.

    Extends ThreeSSBDataSource with girls-specific configuration.
    All scraping methods are inherited - only URLs and ID prefixes differ.

    Public stats pages at https://adidas3ssb.com/girls
    """

    source_type = DataSourceType.THREE_SSB_GIRLS
    source_name = "Adidas 3SSB Girls"
    base_url = "https://adidas3ssb.com/girls"
    region = DataSourceRegion.US

    def __init__(self):
        """
        Initialize 3SSB Girls datasource.

        Inherits all methods from ThreeSSBDataSource parent class.
        Only overrides URLs and ID prefix to point to girls section.
        """
        # Call parent init which sets up HTTP client, rate limiter, logger
        super().__init__()

        # Override 3SSB-specific endpoints for girls section
        # Adidas 3SSB Girls uses same URL structure with /girls prefix
        self.stats_url = f"{self.base_url}/stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"
        self.teams_url = f"{self.base_url}/teams"

        self.logger.info(
            f"Initialized {self.source_name}",
            base_url=self.base_url,
            endpoints={
                "stats": self.stats_url,
                "schedule": self.schedule_url,
                "standings": self.standings_url,
                "teams": self.teams_url,
            },
        )

    def _build_player_id(self, player_name: str, team_name: Optional[str] = None) -> str:
        """
        Build 3SSB Girls player ID.

        Overrides parent to use girls-specific prefix to avoid ID collisions.

        Args:
            player_name: Player's full name
            team_name: Optional team name for uniqueness

        Returns:
            Formatted player ID: "3ssb_g:{name}" or "3ssb_g:{name}:{team}"

        Example:
            "jane_doe" -> "3ssb_g:jane_doe"
            "jane_doe", "Team Elite" -> "3ssb_g:jane_doe:team_elite"
        """
        from ...utils import clean_player_name

        name_part = clean_player_name(player_name).lower().replace(" ", "_")

        if team_name:
            team_part = clean_player_name(team_name).lower().replace(" ", "_")
            return f"3ssb_g:{name_part}:{team_part}"

        return f"3ssb_g:{name_part}"


# Note: All methods (search_players, get_player_season_stats, get_leaderboard, etc.)
# are inherited from ThreeSSBDataSource and work identically.
# The only differences are:
# 1. base_url which changes all endpoint URLs
# 2. _build_player_id which uses "3ssb_g:" prefix instead of "3ssb:"
#
# This design is efficient because:
# 1. No code duplication - reuses all scraping logic
# 2. Maintains consistency between boys and girls adapters
# 3. Easy to maintain - bug fixes to 3SSB apply to both
# 4. Minimal overhead - just URL configuration and ID prefix differences
# 5. ID namespace separation prevents boys/girls player collisions
#
# Usage:
#     three_ssb_girls = ThreeSSBGirlsDataSource()
#     players = await three_ssb_girls.search_players(name="Smith", limit=10)
#     leaders = await three_ssb_girls.get_leaderboard("points", limit=25)
