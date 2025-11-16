"""
Comprehensive Datasource Audit Script

Tests ALL datasources to determine which ones actually provide player statistics.

For each datasource, tests:
1. Can we search for players?
2. Can we get player season stats?
3. What states does it cover?
4. What data quality do we get?

Outputs a comprehensive report showing:
- Which datasources provide player stats âœ…
- Which datasources do NOT provide player stats âŒ
- State coverage by working datasource
- Data quality assessment
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.datasources.base import BaseDataSource
from src.models import Player, PlayerSeasonStats

# Import all US state datasources
from src.datasources.us.bound import BoundDataSource
from src.datasources.us.maxpreps import MaxPrepsDataSource
from src.datasources.us.rankone import RankOneDataSource

# Try to import other datasources (some may not exist yet)
try:
    from src.datasources.us.texas_uil import TexasUILDataSource
except ImportError:
    TexasUILDataSource = None

try:
    from src.datasources.recruiting.on3 import On3DataSource
except ImportError:
    On3DataSource = None

try:
    from src.datasources.recruiting.sports_247 import Sports247DataSource
except ImportError:
    Sports247DataSource = None


class DataSourceAuditor:
    """Audits all datasources to determine player stats capability."""

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    async def test_datasource(
        self,
        name: str,
        datasource_class,
        test_params: Dict
    ) -> Dict:
        """
        Test a single datasource.

        Args:
            name: Datasource name
            datasource_class: Datasource class to instantiate
            test_params: Test parameters (state, search terms, etc.)

        Returns:
            Test results dictionary
        """
        result = {
            "name": name,
            "status": "unknown",
            "player_search": False,
            "player_stats": False,
            "states_covered": [],
            "error": None,
            "sample_data": None,
            "test_params": test_params,
        }

        try:
            print(f"\n{'='*80}")
            print(f"Testing: {name}")
            print(f"{'='*80}")

            # Skip if class not available
            if datasource_class is None:
                result["status"] = "not_implemented"
                result["error"] = "Datasource class not found"
                print(f"âŒ SKIP: {name} - Not implemented")
                return result

            # Initialize datasource
            try:
                datasource = datasource_class()
                print(f"âœ… Initialized {name}")
            except Exception as e:
                result["status"] = "init_failed"
                result["error"] = f"Initialization failed: {str(e)}"
                print(f"âŒ FAIL: Could not initialize - {str(e)}")
                return result

            # Get supported states if available
            if hasattr(datasource, 'SUPPORTED_STATES'):
                result["states_covered"] = datasource.SUPPORTED_STATES
                print(f"ðŸ“ States: {', '.join(datasource.SUPPORTED_STATES)}")

            # Test 1: Search for players
            print(f"\nðŸ” Test 1: Search for players")
            state = test_params.get("state")
            search_name = test_params.get("search_name")

            try:
                players = await datasource.search_players(
                    state=state,
                    name=search_name,
                    limit=5
                )

                if players and len(players) > 0:
                    result["player_search"] = True
                    print(f"âœ… Found {len(players)} players")

                    # Log first player details
                    first_player = players[0]
                    print(f"   Sample: {first_player.full_name}")
                    print(f"   ID: {first_player.player_id}")
                    print(f"   School: {first_player.school_name or 'N/A'}")
                    print(f"   Position: {first_player.position or 'N/A'}")

                    result["sample_data"] = {
                        "player_count": len(players),
                        "sample_player": {
                            "name": first_player.full_name,
                            "id": first_player.player_id,
                            "school": first_player.school_name,
                            "position": str(first_player.position) if first_player.position else None,
                        }
                    }

                    # Test 2: Get player stats
                    print(f"\nðŸ“Š Test 2: Get player season stats")
                    try:
                        stats = await datasource.get_player_season_stats(
                            player_id=first_player.player_id,
                            state=state
                        )

                        if stats:
                            result["player_stats"] = True
                            print(f"âœ… Got season stats")
                            print(f"   Games: {stats.games_played or 'N/A'}")
                            print(f"   Points: {stats.points_total or stats.points_per_game or 'N/A'}")
                            print(f"   Rebounds: {stats.total_rebounds_total or stats.total_rebounds_per_game or 'N/A'}")
                            print(f"   Assists: {stats.assists_total or stats.assists_per_game or 'N/A'}")

                            if result["sample_data"]:
                                result["sample_data"]["stats"] = {
                                    "games": stats.games_played,
                                    "points": stats.points_total or stats.points_per_game,
                                    "rebounds": stats.total_rebounds_total or stats.total_rebounds_per_game,
                                    "assists": stats.assists_total or stats.assists_per_game,
                                }
                        else:
                            print(f"âš ï¸  No stats returned")

                    except Exception as e:
                        print(f"âš ï¸  Stats retrieval failed: {str(e)}")
                        result["error"] = f"Stats failed: {str(e)}"

                else:
                    print(f"âš ï¸  No players found")

            except Exception as e:
                print(f"âš ï¸  Player search failed: {str(e)}")
                result["error"] = f"Search failed: {str(e)}"

            # Determine final status
            if result["player_search"] and result["player_stats"]:
                result["status"] = "working"
                print(f"\nâœ… STATUS: WORKING - Provides player stats")
            elif result["player_search"]:
                result["status"] = "partial"
                print(f"\nâš ï¸  STATUS: PARTIAL - Players only, no stats")
            else:
                result["status"] = "not_working"
                print(f"\nâŒ STATUS: NOT WORKING - No player data")

            # Close datasource
            if hasattr(datasource, 'close'):
                await datasource.close()

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            print(f"\nâŒ ERROR: {str(e)}")

        return result

    async def audit_all(self):
        """Run audit on all datasources."""
        print(f"\n{'#'*80}")
        print(f"# DATASOURCE AUDIT - Player Statistics Validation")
        print(f"# Started: {self.timestamp}")
        print(f"{'#'*80}\n")

        # Define all datasources to test
        datasources_to_test = [
            {
                "name": "GoBound (Iowa)",
                "class": BoundDataSource,
                "params": {"state": "IA", "search_name": None}
            },
            {
                "name": "GoBound (Illinois)",
                "class": BoundDataSource,
                "params": {"state": "IL", "search_name": None}
            },
            {
                "name": "GoBound (Minnesota)",
                "class": BoundDataSource,
                "params": {"state": "MN", "search_name": None}
            },
            {
                "name": "GoBound (South Dakota)",
                "class": BoundDataSource,
                "params": {"state": "SD", "search_name": None}
            },
            {
                "name": "RankOne (Texas)",
                "class": RankOneDataSource,
                "params": {"state": "TX", "search_name": None}
            },
            {
                "name": "RankOne (Kentucky)",
                "class": RankOneDataSource,
                "params": {"state": "KY", "search_name": None}
            },
            {
                "name": "RankOne (Indiana)",
                "class": RankOneDataSource,
                "params": {"state": "IN", "search_name": None}
            },
            {
                "name": "RankOne (Ohio)",
                "class": RankOneDataSource,
                "params": {"state": "OH", "search_name": None}
            },
            {
                "name": "RankOne (Tennessee)",
                "class": RankOneDataSource,
                "params": {"state": "TN", "search_name": None}
            },
            {
                "name": "MaxPreps (California)",
                "class": MaxPrepsDataSource,
                "params": {"state": "CA", "search_name": None}
            },
            {
                "name": "Texas UIL",
                "class": TexasUILDataSource,
                "params": {"state": "TX", "search_name": None}
            },
            {
                "name": "On3 Recruiting",
                "class": On3DataSource,
                "params": {"state": None, "search_name": None}
            },
            {
                "name": "247Sports Recruiting",
                "class": Sports247DataSource,
                "params": {"state": None, "search_name": None}
            },
        ]

        # Test each datasource
        for ds_config in datasources_to_test:
            result = await self.test_datasource(
                ds_config["name"],
                ds_config["class"],
                ds_config["params"]
            )
            self.results[ds_config["name"]] = result

        # Generate summary
        self.generate_summary()

    def generate_summary(self):
        """Generate and display summary report."""
        print(f"\n\n{'#'*80}")
        print(f"# AUDIT SUMMARY")
        print(f"{'#'*80}\n")

        # Categorize results
        working = []
        partial = []
        not_working = []
        not_implemented = []
        errors = []

        for name, result in self.results.items():
            if result["status"] == "working":
                working.append(name)
            elif result["status"] == "partial":
                partial.append(name)
            elif result["status"] == "not_working":
                not_working.append(name)
            elif result["status"] == "not_implemented":
                not_implemented.append(name)
            elif result["status"] == "error":
                errors.append(name)

        # Display summary
        print(f"âœ… WORKING (Player Stats Available): {len(working)}")
        for name in working:
            states = self.results[name].get("states_covered", [])
            states_str = f" [{', '.join(states)}]" if states else ""
            print(f"   - {name}{states_str}")

        print(f"\nâš ï¸  PARTIAL (Players Only, No Stats): {len(partial)}")
        for name in partial:
            print(f"   - {name}")

        print(f"\nâŒ NOT WORKING (No Player Data): {len(not_working)}")
        for name in not_working:
            print(f"   - {name}")

        print(f"\nðŸ”¨ NOT IMPLEMENTED: {len(not_implemented)}")
        for name in not_implemented:
            print(f"   - {name}")

        print(f"\nðŸš¨ ERRORS: {len(errors)}")
        for name in errors:
            error = self.results[name].get("error", "Unknown error")
            print(f"   - {name}: {error}")

        # State coverage summary
        print(f"\n\n{'='*80}")
        print(f"STATE COVERAGE BY WORKING DATASOURCES")
        print(f"{'='*80}\n")

        state_coverage = {}
        for name, result in self.results.items():
            if result["status"] == "working":
                for state in result.get("states_covered", []):
                    if state not in state_coverage:
                        state_coverage[state] = []
                    state_coverage[state].append(name)

        if state_coverage:
            for state in sorted(state_coverage.keys()):
                sources = state_coverage[state]
                print(f"{state}: {', '.join(sources)}")
        else:
            print("No state coverage from working datasources")

        # Save results to file
        output_file = Path("data/debug/datasource_audit_results.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": self.timestamp,
                "summary": {
                    "working": len(working),
                    "partial": len(partial),
                    "not_working": len(not_working),
                    "not_implemented": len(not_implemented),
                    "errors": len(errors),
                },
                "state_coverage": state_coverage,
                "detailed_results": self.results,
            }, f, indent=2, default=str)

        print(f"\n\nðŸ“„ Full results saved to: {output_file}")


async def main():
    """Run the audit."""
    auditor = DataSourceAuditor()
    await auditor.audit_all()


if __name__ == '__main__':
    asyncio.run(main())
