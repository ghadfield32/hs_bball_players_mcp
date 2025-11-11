"""
Nike Girls EYBL (Elite Youth Basketball League) DataSource Adapter

Extends the boys EYBL adapter for girls basketball statistics.
Reuses all scraping logic from the base EYBL adapter with girls-specific URLs.
"""

from datetime import datetime
from typing import Optional

from ...models import DataSourceRegion, DataSourceType
from .eybl import EYBLDataSource


class EYBLGirlsDataSource(EYBLDataSource):
    """
    Nike Girls EYBL data source adapter.

    Extends EYBLDataSource with girls-specific configuration.
    All scraping methods are inherited - only URLs differ.

    Public stats pages at https://nikeeyb.com/girls
    """

    source_type = DataSourceType.EYBL_GIRLS
    source_name = "Nike Girls EYBL"
    base_url = "https://nikeeyb.com/girls"
    region = DataSourceRegion.US

    def __init__(self):
        """
        Initialize Girls EYBL datasource.

        Inherits all methods from EYBLDataSource parent class.
        Only overrides URLs to point to girls section.
        """
        # Call parent init which sets up HTTP client, rate limiter, logger
        super().__init__()

        # Override EYBL-specific endpoints for girls section
        # Nike Girls EYBL uses same URL structure with /girls prefix
        self.stats_url = f"{self.base_url}/cumulative-season-stats"
        self.schedule_url = f"{self.base_url}/schedule"
        self.standings_url = f"{self.base_url}/standings"

        self.logger.info(
            f"Initialized {self.source_name}",
            base_url=self.base_url,
            endpoints={
                "stats": self.stats_url,
                "schedule": self.schedule_url,
                "standings": self.standings_url,
            },
        )


# Note: All methods (search_players, get_player_season_stats, get_leaderboard, etc.)
# are inherited from EYBLDataSource and work identically.
# The only difference is the base_url which changes all endpoint URLs.
#
# This design is efficient because:
# 1. No code duplication - reuses all scraping logic
# 2. Maintains consistency between boys and girls adapters
# 3. Easy to maintain - bug fixes to EYBL apply to both
# 4. Minimal overhead - just URL configuration differences
#
# Usage:
#     eybl_girls = EYBLGirlsDataSource()
#     players = await eybl_girls.search_players(name="Smith", limit=10)
#     leaders = await eybl_girls.get_leaderboard("points", limit=25)
