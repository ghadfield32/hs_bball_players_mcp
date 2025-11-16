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
=======
"""
Comprehensive Datasource Audit Script

This script tests all 56 configured datasources to identify:
1. Which adapters can successfully connect to their target websites
2. Which adapters are blocked (403/401/etc.)
3. Which adapters have working data extraction
4. Which adapters need browser automation
5. Which adapters have broken/defunct domains
6. Overall datasource health status

This provides a complete picture of what needs to be fixed.
"""

import asyncio
import httpx
from datetime import datetime
import json


# All configured datasources from the project
DATASOURCES = {
    # US National Circuits
    "EYBL Boys": "https://nikeeyb.com/cumulative-season-stats",
    "EYBL Girls": "https://nikeeyb.com/girls/cumulative-season-stats",
    "3SSB Boys": "https://adidas3ssb.com/stats",
    "3SSB Girls": "https://adidas3ssb.com/girls/stats",
    "UAA Boys": "https://uaassociation.com/stats",
    "UAA Girls": "https://uanext.com/stats",

    # US Multi-State
    "SBLive WA": "https://wa.sblive.com/high-school/boys-basketball/stats",
    "Bound IA": "https://www.ia.bound.com/stats",
    "MN Basketball Hub": "https://www.mnbasketballhub.com/stats",

    # US Single State
    "PSAL NYC": "https://www.psal.org/sports/basketball",
    "WSN Wisconsin": "https://www.wissports.net/basketball",

    # US Prep/Elite
    "OTE": "https://overtimeelite.com/stats",
    "Grind Session": "https://thegrindsession.com/stats",
    "NEPSAC": "https://www.nepsac.org/landing/index",

    # Global/International
    "FIBA Youth": "https://www.fiba.basketball/youth",
    "FIBA LiveStats": "https://livefiba.dcd.shared.geniussports.com",
    "ANGT": "https://www.euroleaguebasketball.net/next-generation",
    "NBBL (Germany)": "https://www.nbbl-basketball.de/stats",
    "FEB (Spain)": "https://www.feb.es/competiciones",
    "MKL (Lithuania)": "https://www.lkl.lt/mkl",
    "LNB Espoirs (France)": "https://www.lnb.fr/espoirs",

    # Canada
    "OSBA": "https://www.osba.ca",
    "NPA Canada": "https://npacanada.com/stats",

    # Australia
    "PlayHQ": "https://www.playhq.com/basketball-australia",

    # State Associations (Sample - top basketball states)
    "Florida FHSAA": "https://www.fhsaa.org/basketball",
    "Georgia GHSA": "https://www.ghsa.net/sports/basketball",
    "North Carolina NCHSAA": "https://www.nchsaa.org/sports/basketball",
    "Texas UIL": "https://www.uiltexas.org/basketball",
    "California CIF": "https://www.cifstate.org/basketball",
    "New York NYSPHSAA": "https://www.nysphsaa.org/sports/basketball",
    "Illinois IHSA": "https://www.ihsa.org/Sports-Activities/Boys-Basketball",
    "Pennsylvania PIAA": "https://www.piaa.org/sports/basketball",
    "Ohio OHSAA": "https://www.ohsaa.org/sports/basketball",
    "Michigan MHSAA": "https://www.mhsaa.com/sports/basketball",
}


async def test_datasource(name: str, url: str, client: httpx.AsyncClient):
    """Test a single datasource for connectivity and basic functionality."""
    result = {
        "name": name,
        "url": url,
        "status": "UNKNOWN",
        "http_status": None,
        "error": None,
        "response_size": 0,
        "has_content": False,
        "needs_browser": False,
        "recommendation": ""
    }

    try:
        # Test with standard HTTP client
        response = await client.get(url, timeout=15.0)
        result["http_status"] = response.status_code
        result["response_size"] = len(response.text)

        if response.status_code == 200:
            result["status"] = "SUCCESS"
            result["has_content"] = len(response.text) > 1000

            # Check for indicators that stats might be available
            content_lower = response.text.lower()
            if any(keyword in content_lower for keyword in ['stats', 'statistics', 'player', 'team']):
                result["recommendation"] = "✅ GOOD - Site accessible, content found"
            else:
                result["recommendation"] = "⚠️  WARNING - Accessible but may lack stats"

        elif response.status_code == 403:
            result["status"] = "BLOCKED"
            result["needs_browser"] = True
            result["recommendation"] = "🛑 BLOCKED - Needs browser automation (anti-bot protection)"

        elif response.status_code == 404:
            result["status"] = "NOT_FOUND"
            result["recommendation"] = "❌ BROKEN - Page not found (404)"

        elif response.status_code == 401:
            result["status"] = "AUTH_REQUIRED"
            result["recommendation"] = "🔒 AUTH - Requires authentication"

        elif response.status_code in [301, 302, 307, 308]:
            result["status"] = "REDIRECT"
            result["recommendation"] = f"🔄 REDIRECT - Redirects to {response.headers.get('Location', 'unknown')}"

        else:
            result["status"] = "HTTP_ERROR"
            result["recommendation"] = f"⚠️  HTTP {response.status_code}"

    except httpx.ConnectTimeout:
        result["status"] = "TIMEOUT"
        result["error"] = "Connection timeout"
        result["recommendation"] = "⏱️  TIMEOUT - Server not responding"

    except httpx.ConnectError as e:
        result["status"] = "UNREACHABLE"
        result["error"] = str(e)
        result["recommendation"] = "💀 UNREACHABLE - Domain may be defunct"

    except Exception as e:
        result["status"] = "ERROR"
        result["error"] = str(e)[:200]
        result["recommendation"] = f"❌ ERROR - {str(e)[:100]}"

    return result


async def audit_all_datasources():
    """Run comprehensive audit of all datasources."""
    print("=" * 100)
    print("COMPREHENSIVE DATASOURCE AUDIT")
    print(f"Testing {len(DATASOURCES)} datasources...")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)

    results = []

    # Configure HTTP client with realistic headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=15.0,
        follow_redirects=True,
        verify=False  # Ignore SSL errors for testing
    ) as client:

        # Test each datasource
        tasks = []
        for name, url in DATASOURCES.items():
            task = test_datasource(name, url, client)
            tasks.append(task)

        # Run tests concurrently (in batches to avoid overwhelming servers)
        batch_size = 10
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch)
            results.extend(batch_results)

            # Brief pause between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(2)

    # Analyze results
    print("\n" + "=" * 100)
    print("DETAILED RESULTS")
    print("=" * 100)

    # Group by status
    by_status = {}
    for result in results:
        status = result["status"]
        if status not in by_status:
            by_status[status] = []
        by_status[status].append(result)

    # Print detailed results by category
    categories = [
        ("SUCCESS", "✅ WORKING DATASOURCES"),
        ("BLOCKED", "🛑 BLOCKED BY ANTI-BOT (Need Browser Automation)"),
        ("NOT_FOUND", "❌ BROKEN (404 Not Found)"),
        ("UNREACHABLE", "💀 UNREACHABLE (Defunct Domain?)"),
        ("TIMEOUT", "⏱️  TIMEOUT (Server Issues)"),
        ("AUTH_REQUIRED", "🔒 REQUIRES AUTHENTICATION"),
        ("REDIRECT", "🔄 REDIRECTS"),
        ("HTTP_ERROR", "⚠️  HTTP ERRORS"),
        ("ERROR", "❌ OTHER ERRORS"),
    ]

    for status, title in categories:
        if status in by_status:
            print(f"\n{title} ({len(by_status[status])})")
            print("-" * 100)
            for result in by_status[status]:
                print(f"  {result['name']:30s} | {result['recommendation']}")
                if result['error']:
                    print(f"      Error: {result['error'][:100]}")

    # Summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)

    total = len(results)
    success = len(by_status.get("SUCCESS", []))
    blocked = len(by_status.get("BLOCKED", []))
    broken = len(by_status.get("NOT_FOUND", [])) + len(by_status.get("UNREACHABLE", []))
    needs_fix = total - success

    print(f"Total Datasources Tested: {total}")
    print(f"✅ Working (HTTP 200):    {success} ({success/total*100:.1f}%)")
    print(f"🛑 Blocked (403):         {blocked} ({blocked/total*100:.1f}%)")
    print(f"❌ Broken (404/defunct):  {broken} ({broken/total*100:.1f}%)")
    print(f"⚠️  Needs Attention:      {needs_fix} ({needs_fix/total*100:.1f}%)")

    # Priority recommendations
    print("\n" + "=" * 100)
    print("PRIORITY RECOMMENDATIONS")
    print("=" * 100)

    print("\n🔥 HIGH PRIORITY - Fix These First:")
    high_priority = []
    for result in results:
        if result["status"] == "BLOCKED" and any(keyword in result["name"] for keyword in ["EYBL", "ANGT", "OSBA", "3SSB", "UAA"]):
            high_priority.append(result["name"])
    for name in high_priority:
        print(f"  - {name}: Implement browser automation")

    print("\n🔧 MEDIUM PRIORITY - Investigate & Fix:")
    medium_priority = []
    for result in results:
        if result["status"] in ["NOT_FOUND", "UNREACHABLE"]:
            medium_priority.append(f"{result['name']}: {result['recommendation']}")
    for item in medium_priority[:10]:  # Limit to top 10
        print(f"  - {item}")

    print("\n✅ LOW PRIORITY - Verify Data Extraction:")
    for result in results[:5]:  # Show first 5 working sources
        if result["status"] == "SUCCESS":
            print(f"  - {result['name']}: Test actual stat extraction")

    # Export results to JSON
    output_file = "datasource_audit_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tested": total,
            "summary": {
                "success": success,
                "blocked": blocked,
                "broken": broken,
                "needs_fix": needs_fix
            },
            "results": results
        }, f, indent=2)

    print(f"\n📄 Full results exported to: {output_file}")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    # Disable SSL warnings
    import warnings
    warnings.filterwarnings('ignore')

    asyncio.run(audit_all_datasources())